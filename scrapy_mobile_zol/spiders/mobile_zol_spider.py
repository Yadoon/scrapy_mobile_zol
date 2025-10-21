import re
import scrapy
from scrapy import Selector
import re


class MobileZolSpider(scrapy.Spider):
    name = 'mobile_scrapy'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }

    # 测试时可以只爬取第一页，避免请求过多
    start_urls = []
    for i in range(1, 99):  # 只爬取第一页用于测试
        start_url = 'http://detail.zol.com.cn/cell_phone_index/subcate57_0_list_1_0_1_2_0_{}.html'.format(i)
        start_urls.append(start_url)

    def parse(self, response):
        phone_list = response.xpath('//*[@id="J_PicMode"]/li')
        self.logger.info(f"找到 {len(phone_list)} 个手机产品")

        for phone_item in phone_list:
            stats = {}
            try:
                phone_price = phone_item.xpath('div[1]/span[2]/b[2]/text()').extract_first()  # 价格
                stats['phone_price'] = phone_price if phone_price else 0
            except Exception as e:
                self.logger.error(f"提取价格出错: {e}")
                stats['phone_price'] = 0

            try:
                phone_name = phone_item.xpath('h3/a/text()').extract_first()
                if not phone_name:
                    continue
                stats['phone_name'] = phone_name.lower()  # 手机名称
            except Exception as e:
                self.logger.error(f"提取手机名称出错: {e}")
                continue

            try:
                phone_info_url = response.urljoin(phone_item.xpath('a/@href').extract_first())
                if not phone_info_url:
                    continue
                stats['phone_info_url'] = phone_info_url
                self.logger.info(f"正在爬取手机: {phone_name}")
            except Exception as e:
                self.logger.error(f"提取详情链接出错: {e}")
                continue

            yield scrapy.Request(
                url=phone_info_url,
                headers=self.headers,
                meta={"stats": stats},
                callback=self.parse_phone_info,
                dont_filter=True
            )

    def parse_phone_info(self, response):
        stats = response.meta['stats']

        try:
            # 获取手机参数详情链接 - 这是关键！参数通常在专门的参数页面
            phone_parameter = response.xpath('//*[@id="_j_tag_nav"]/ul/li[2]')
            if not phone_parameter:
                # 尝试其他可能的参数链接位置
                phone_parameter = response.xpath('//a[contains(text(), "参数") or contains(@title, "参数")]')

            phone_parameter_url = response.urljoin(phone_parameter.xpath("@href").extract_first())
            if phone_parameter_url:
                stats['phone_parameter_url'] = phone_parameter_url
                # 跳转到参数详情页获取完整参数信息
                self.logger.info(f"跳转到参数详情页: {phone_parameter_url}")
                return scrapy.Request(
                    url=phone_parameter_url,
                    headers=self.headers,
                    meta={"stats": stats},
                    callback=self.parse_phone_parameter,
                    dont_filter=True
                )
        except Exception as e:
            self.logger.error(f"获取参数链接出错: {e}")

        # 如果无法获取参数链接，则尝试直接从当前页面提取参数
        self.logger.warning(f"无法获取参数链接，尝试直接从当前页面提取参数")
        return self.extract_params_from_current_page(response, stats)

    def parse_phone_parameter(self, response):
        stats = response.meta['stats']
        self.logger.info(f"正在解析参数页面: {response.url}")

        try:
            # 尝试找到"完整参数"或"全部参数"的链接 - 用户反馈需要二次跳转
            full_param_links = response.xpath('//a[contains(text(), "完整参数") or contains(text(), "全部参数")]')

            if full_param_links:
                full_param_url = response.urljoin(full_param_links.xpath("@href").extract_first())
                if full_param_url:
                    self.logger.info(f"发现完整参数链接，跳转到: {full_param_url}")
                    # 跳转到完整参数页面
                    return scrapy.Request(
                        url=full_param_url,
                        headers=self.headers,
                        meta={"stats": stats},
                        callback=self.parse_full_parameters,
                        dont_filter=True
                    )
            else:
                self.logger.info("未找到完整参数链接，尝试直接从当前参数页面提取")
        except Exception as e:
            self.logger.error(f"查找完整参数链接出错: {e}")

        # 如果没有找到完整参数链接，或者跳转出错，则直接从当前参数页面提取
        return self.extract_parameters_from_current_page(response, stats)

    def parse_full_parameters(self, response):
        """从完整参数页面提取详细参数"""
        stats = response.meta['stats']
        self.logger.info(f"正在解析完整参数页面: {response.url}")

        # 从完整参数页面提取详细参数
        return self.extract_parameters_from_current_page(response, stats)

    def extract_parameters_from_current_page(self, response, stats):
        """从当前页面（参数页或完整参数页）提取详细参数"""
        try:
            # 初始化字段
            # 尝试多种XPath表达式提取上市日期
            release_date = None
            # 1. 原始XPath（我们在静态文件中看到的结构）
            release_date = response.xpath(
                '//th[span[normalize-space(.)="上市日期"]]/following-sibling::td/span/text()').extract_first()

            # 2. 更通用的XPath表达式（不依赖于span标签）
            if not release_date:
                release_date = response.xpath(
                    '//th[contains(text(), "上市日期") or contains(@title, "上市日期")]/following-sibling::td//text()').extract_first()
                if release_date: release_date = release_date.strip()

            # 3. 尝试使用关键词查找
            if not release_date:
                date_elements = response.xpath(
                    '//*[contains(text(), "上市日期") or contains(@title, "上市日期")]/following::*[1]')
                if date_elements:
                    release_date = date_elements.xpath("string()").extract_first().strip()

            stats['release_date'] = release_date if release_date else ''
            self.logger.info(f"上市日期: {stats['release_date']}")

            # 提取出厂系统内核
            # 1. 原始XPath
            os_value = response.xpath(
                '//th[span[normalize-space(.)="出厂系统内核"]]/following-sibling::td/span/text()').extract_first()

            # 2. 更通用的XPath
            if not os_value:
                os_value = response.xpath(
                    '//th[contains(text(), "出厂系统") or contains(@title, "出厂系统")]/following-sibling::td//text()').extract_first()
                if os_value: os_value = os_value.strip()

            # 3. 尝试使用关键词查找
            if not os_value:
                os_elements = response.xpath(
                    '//*[contains(text(), "出厂系统") or contains(@title, "出厂系统")]/following::*[1]')
                if os_elements:
                    os_value = os_elements.xpath("string()").extract_first().strip()

            stats['os'] = os_value if os_value else ''
            self.logger.info(f"出厂系统内核: {stats['os']}")

            # 提取操作系统
            # 1. 原始XPath
            vendor_os = response.xpath(
                '//th[span[normalize-space(.)="操作系统"]]/following-sibling::td/span/text()').extract_first()

            # 2. 更通用的XPath
            if not vendor_os:
                vendor_os = response.xpath(
                    '//th[contains(text(), "操作系统") or contains(@title, "操作系统")]/following-sibling::td//text()').extract_first()
                if vendor_os: vendor_os = vendor_os.strip()

            # 3. 尝试使用关键词查找
            if not vendor_os:
                os_elements = response.xpath(
                    '//*[contains(text(), "操作系统") or contains(@title, "操作系统")]/following::*[1]')
                if os_elements:
                    vendor_os = os_elements.xpath("string()").extract_first().strip()

            stats['vendor_os'] = vendor_os.split('>更多')[0].strip() if vendor_os else ''
            self.logger.info(f"操作系统: {stats['vendor_os']}")

            # 提取屏幕尺寸
            # 1. 原始XPath
            screen_size = response.xpath(
                '//th[span[normalize-space(.)="屏幕尺寸"]]/following-sibling::td/span/text()').extract_first()

            # 2. 更通用的XPath
            if not screen_size:
                screen_size = response.xpath(
                    '//th[contains(text(), "屏幕尺寸") or contains(@title, "屏幕尺寸")]/following-sibling::td//text()').extract_first()
                if screen_size: screen_size = screen_size.strip()

            # 3. 尝试使用关键词查找
            if not screen_size:
                size_elements = response.xpath(
                    '//*[contains(text(), "屏幕尺寸") or contains(@title, "屏幕尺寸")]/following::*[1]')
                if size_elements:
                    screen_size = size_elements.xpath("string()").extract_first().strip()


            # 提取英寸数字
            if screen_size:
                try:
                    match = re.search('([\d.]+)英寸', screen_size)
                    if match:
                        screen_size = float(match.group(1))
                except:
                    pass
            stats['screen_size'] = screen_size
            self.logger.info(f"屏幕尺寸: {stats['screen_size']}")
            
            # 填充phone_size字段（保持向后兼容）
            stats['phone_size'] = screen_size if screen_size else 0.0

            # 提取CPU型号 - 只获取span标签内容，不包括后续的i标签和超链接
            cpu_model = None
            # 1. 原始XPath - 只获取span标签中的文本
            cpu_model = response.xpath(
                '//th[span[normalize-space(.)="CPU型号"]]/following-sibling::td/span/text()').extract_first()

            # 2. 更通用的XPath
            if not cpu_model:
                cpu_model = response.xpath(
                    '//th[contains(text(), "CPU型号") or contains(@title, "CPU型号")]/following-sibling::td/span/text()').extract_first()
                if cpu_model: cpu_model = cpu_model.strip()

            # 3. 尝试使用关键词查找
            if not cpu_model:
                cpu_elements = response.xpath(
                    '//*[contains(text(), "CPU型号") or contains(@title, "CPU型号")]/following::td//span')
                if cpu_elements:
                    cpu_model = cpu_elements.xpath("text()").extract_first()
                    if cpu_model: cpu_model = cpu_model.strip()

            # 确保只保留CPU型号文本，过滤掉任何可能的链接或标签
            if cpu_model:
                # 清理可能的HTML标签或链接文本
                cpu_model = re.sub(r'<[^>]*>', '', cpu_model)
                cpu_model = cpu_model.split('<')[0].strip()  # 移除可能的链接部分

            stats['cpu_model'] = cpu_model if cpu_model else ''
            self.logger.info(f"CPU型号: {stats['cpu_model']}")

            # 提取GPU型号 - 只获取span标签内容，不包括后续的i标签和超链接
            gpu_model = None
            # 1. 原始XPath - 只获取span标签中的文本
            gpu_model = response.xpath(
                '//th[span[normalize-space(.)="GPU型号"]]/following-sibling::td/span/text()').extract_first()

            # 2. 更通用的XPath
            if not gpu_model:
                gpu_model = response.xpath(
                    '//th[contains(text(), "GPU型号") or contains(@title, "GPU型号")]/following-sibling::td/span/text()').extract_first()
                if gpu_model: gpu_model = gpu_model.strip()

            # 3. 尝试使用关键词查找
            if not gpu_model:
                gpu_elements = response.xpath(
                    '//*[contains(text(), "GPU型号") or contains(@title, "GPU型号")]/following::td//span')
                if gpu_elements:
                    gpu_model = gpu_elements.xpath("text()").extract_first()
                    if gpu_model: gpu_model = gpu_model.strip()

            # 确保只保留GPU型号文本，过滤掉任何可能的链接或标签
            if gpu_model:
                # 清理可能的HTML标签或链接文本
                gpu_model = re.sub(r'<[^>]*>', '', gpu_model)
                gpu_model = gpu_model.split('<')[0].strip()  # 移除可能的链接部分

            stats['gpu_model'] = gpu_model if gpu_model else ''
            self.logger.info(f"GPU型号: {stats['gpu_model']}")
            
            # 提取分辨率信息用于填充phone_x和phone_y
            try:
                # 尝试从参数页面提取分辨率信息 - 方法1:原始XPath
                resolution = response.xpath(
                    '//th[contains(text(), "分辨率") or contains(@title, "分辨率")]/following-sibling::td//text()').extract_first()
                
                # 方法2: 如果方法1失败，尝试更通用的XPath
                if not resolution:
                    resolution = response.xpath(
                        '//*[contains(text(), "分辨率") or contains(@title, "分辨率")]/following::*[1]/text()').extract_first()
                
                # 方法3: 如果前两种方法都失败，尝试获取包含"x"的像素信息
                if not resolution:
                    resolution_elements = response.xpath(
                        '//td[contains(text(), "x") and contains(text(), "像素")]/text()').extract()
                    if resolution_elements:
                        resolution = resolution_elements[0]
                
                # 打印调试信息
                self.logger.debug(f"提取到的分辨率信息: {resolution}")
                
                if resolution:
                    resolution = resolution.strip()
                    # 匹配不同格式的分辨率，如1080x2340, 1080×2340, 1080× 2340等
                    resolution_match = re.search(r"(\d+)\s*[x×]\s*(\d+)", resolution)
                    if resolution_match:
                        stats['phone_x'] = int(resolution_match.group(2))
                        stats['phone_y'] = int(resolution_match.group(1))
                    else:
                        # 尝试直接从文本中提取数字
                        nums = re.findall(r"\d+", resolution)
                        if len(nums) >= 2:
                            stats['phone_x'] = int(nums[1])
                            stats['phone_y'] = int(nums[0])
                        else:
                            stats['phone_x'] = 0
                            stats['phone_y'] = 0
                else:
                    stats['phone_x'] = 0
                    stats['phone_y'] = 0
                    self.logger.warning("未能提取到分辨率信息")
            except Exception as e:
                stats['phone_x'] = 0
                stats['phone_y'] = 0
                self.logger.error(f"提取分辨率时出错: {e}")
                
            # 生成phone_info字段 - 组合主要参数信息
            phone_info_parts = []
            if stats.get('phone_name'):
                phone_info_parts.append(f"手机名称: {stats['phone_name']}")
            if stats.get('screen_size'):
                phone_info_parts.append(f"屏幕尺寸: {stats['screen_size']}")
            if stats.get('cpu_model'):
                phone_info_parts.append(f"CPU型号: {stats['cpu_model']}")
            if stats.get('os'):
                phone_info_parts.append(f"系统: {stats['os']}")
            if stats.get('release_date'):
                phone_info_parts.append(f"上市日期: {stats['release_date']}")
                
            stats['phone_info'] = ", ".join(phone_info_parts)

        except Exception as e:
            self.logger.error(f"提取参数时出错: {e}")

        # 补充获取品牌信息
        try:
            phone_brand = response.xpath('//*[@id="_j_breadcrumb"]/text()').extract_first()
            if phone_brand:
                stats['phone_brand'] = phone_brand
        except:
            pass

        yield stats

    def extract_params_from_current_page(self, response, stats):
        """当无法获取参数详情页时，尝试从当前页面提取参数"""
        try:
            # 获取手机品牌
            phone_brand = response.xpath('//*[@id="_j_breadcrumb"]/text()').extract_first()
            stats['phone_brand'] = phone_brand if phone_brand else ''

            # 获取手机所有基本信息
            phone_info_xpaths = response.xpath('//*[@class="product-link"]')
            phone_info = ''
            for phone_info_item in phone_info_xpaths:
                text = phone_info_item.xpath("text()").extract_first()
                if text:
                    phone_info = text + ", " + phone_info
            stats['phone_info'] = phone_info

            # 获取手机尺寸
            try:
                if len(phone_info_xpaths) > 1:
                    phone_size_text = phone_info_xpaths[-2].xpath("text()").extract_first()
                    if phone_size_text:
                        try:
                            phone_size = float(re.search('(.+)英寸', phone_size_text).group(1))
                            stats['phone_size'] = phone_size
                        except:
                            stats['phone_size'] = 0.0
            except:
                stats['phone_size'] = 0.0

            # 获取手机分辨率
            try:
                if len(phone_info_xpaths) > 0:
                    phone_resolution = response.xpath('//*[contains(text(), "分辨率") or contains(@title, "分辨率")]/following::*[1]/text()').extract_first()
                    if phone_resolution:
                        try:
                            resolution_match = re.search(r"(\d+)x(\d+)", phone_resolution)
                            if resolution_match:
                                stats['phone_x'] = int(resolution_match.group(2))
                                stats['phone_y'] = int(resolution_match.group(1))
                            else:
                                stats['phone_x'] = 0
                                stats['phone_y'] = 0
                        except:
                            stats['phone_x'] = 0
                            stats['phone_y'] = 0
            except:
                stats['phone_x'] = 0
                stats['phone_y'] = 0

            # 尝试直接从当前页面提取关键参数
            # 使用更通用的XPath表达式，适应不同的页面结构
            release_date = response.xpath(
                '//*[contains(text(), "上市日期") or contains(@title, "上市日期")]/following::*[1]/text()').extract_first()
            stats['release_date'] = release_date if release_date else ''

            os_value = response.xpath(
                '//*[contains(text(), "出厂系统") or contains(@title, "出厂系统")]/following::*[1]/text()').extract_first()
            stats['os'] = os_value if os_value else ''

            vendor_os = response.xpath(
                '//*[contains(text(), "操作系统") or contains(@title, "操作系统")]/following::*[1]/text()').extract_first()
            stats['vendor_os'] = vendor_os if vendor_os else ''

        except Exception as e:
            self.logger.error(f"从当前页面提取参数时出错: {e}")

        return stats
