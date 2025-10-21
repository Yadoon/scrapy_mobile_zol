import requests
from lxml import etree
import logging
import re

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 测试URL - 从之前爬取的结果中选择一个手机页面
# 我们选择vivo X300 Pro作为测试样例
TEST_URL = "https://detail.zol.com.cn/cell_phone/index2142394.shtml"
# 尝试不同的参数页面URL格式
PARAM_URLS = [
    TEST_URL.replace("index", "param"),  # 尝试替换index为param
    TEST_URL.replace("shtml", "param.shtml"),  # 尝试添加param
    TEST_URL + "#param",  # 尝试添加锚点
    "https://detail.zol.com.cn/param/index2142394.shtml",  # 尝试不同的路径
    "https://detail.zol.com.cn/parameter/index2142394.shtml"  # 尝试parameter关键词
]

# 添加请求头，模拟浏览器访问
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Referer': TEST_URL,  # 添加引用页，避免被识别为爬虫
}

def try_decode_content(content):
    """尝试多种编码方式解码内容，解决乱码问题"""
    encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
    
    for encoding in encodings:
        try:
            decoded = content.decode(encoding)
            return decoded, encoding
        except UnicodeDecodeError:
            continue
    
    # 如果所有编码都失败，使用replace模式
    return content.decode('utf-8', errors='replace'), 'utf-8 (with errors)'

def extract_parameters_from_html(html_content, url):
    """从HTML内容中提取手机参数"""
    # 保存当前URL的HTML样本
    url_hash = re.sub(r'[^a-zA-Z0-9]', '_', url[:50])
    sample_file = f"page_sample_{url_hash}.html"
    
    with open(sample_file, "w", encoding="utf-8") as f:
        # 只保存前10000个字符，避免文件过大
        f.write(html_content[:10000])
    
    tree = etree.HTML(html_content)
    params = {}
    
    # 调试：打印页面标题（尝试处理乱码）
    title = tree.xpath('//title/text()')
    logger.info(f"页面标题: {title}")
    
    # 1. 尝试原始的XPath表达式（我们在静态文件中看到的结构）
    logger.info("尝试原始XPath表达式...")
    release_date_1 = tree.xpath('//th[span[normalize-space(.)="上市日期"]]/following-sibling::td/span/text()')
    os_1 = tree.xpath('//th[span[normalize-space(.)="出厂系统内核"]]/following-sibling::td/span/text()')
    vendor_os_1 = tree.xpath('//th[span[normalize-space(.)="操作系统"]]/following-sibling::td/span/text()')
    
    logger.info(f"原始XPath - 上市日期: {release_date_1}")
    logger.info(f"原始XPath - 出厂系统内核: {os_1}")
    logger.info(f"原始XPath - 操作系统: {vendor_os_1}")
    
    # 2. 尝试更通用的XPath表达式（不依赖于span标签）
    logger.info("\n尝试更通用的XPath表达式...")
    release_date_2 = tree.xpath('//th[contains(text(), "上市日期") or contains(@title, "上市日期")]/following-sibling::td//text()')
    os_2 = tree.xpath('//th[contains(text(), "出厂系统") or contains(@title, "出厂系统")]/following-sibling::td//text()')
    vendor_os_2 = tree.xpath('//th[contains(text(), "操作系统") or contains(@title, "操作系统")]/following-sibling::td//text()')
    
    logger.info(f"通用XPath - 上市日期: {release_date_2}")
    logger.info(f"通用XPath - 出厂系统内核: {os_2}")
    logger.info(f"通用XPath - 操作系统: {vendor_os_2}")
    
    # 3. 尝试查找所有的参数表格
    logger.info("\n尝试查找所有参数表格...")
    param_tables = tree.xpath('//table')
    logger.info(f"找到 {len(param_tables)} 个表格")
    
    # 如果找到表格，尝试分析第一个表格的结构
    if param_tables:
        logger.info("分析第一个表格结构:")
        first_table_html = etree.tostring(param_tables[0], encoding='unicode', pretty_print=True)
        # 只打印前500个字符
        logger.info(f"表格HTML样本: {first_table_html[:500]}...")
    
    # 4. 尝试查找包含特定关键词的所有元素
    logger.info("\n尝试查找包含特定关键词的元素...")
    all_release_dates = tree.xpath('//*[contains(text(), "上市日期") or contains(@title, "上市日期")]')
    logger.info(f"包含'上市日期'的元素数量: {len(all_release_dates)}")
    
    # 打印一些包含关键词的元素上下文
    for i, elem in enumerate(all_release_dates[:3]):  # 只打印前3个
        context = etree.tostring(elem.getparent(), encoding='unicode', pretty_print=True)
        logger.info(f"上市日期元素上下文 {i+1}: {context[:300]}...")
    
    # 5. 尝试使用属性值查找（更通用的模式）
    logger.info("\n尝试使用属性值查找...")
    # 查找id包含"Pm"或"param"的元素，这可能是参数相关的模式
    param_patterns = ['Pm', 'param', 'spec', '规格', '参数']
    
    for pattern in param_patterns:
        param_name_elements = tree.xpath(f'//*[contains(@id, "{pattern}") or contains(@class, "{pattern}")]')
        logger.info(f"找到包含'{pattern}'的元素数量: {len(param_name_elements)}")
        
        # 打印一些样本元素
        for i, elem in enumerate(param_name_elements[:3]):  # 只打印前3个
            # 修复：使用正确的方法获取元素文本
            elem_text = elem.xpath("string()").strip()  # 使用xpath string()函数获取所有文本
            elem_id = elem.get("id", "无ID")
            elem_class = elem.get("class", "无class")
            logger.info(f"  元素{i+1}: {elem_text[:50]}... (ID: {elem_id}, Class: {elem_class})" )
    
    # 6. 尝试使用正则表达式直接在HTML文本中查找参数
    logger.info("\n尝试使用正则表达式直接查找参数...")
    
    # 查找上市日期
    release_date_match = re.search(r'上市日期[^<]*<[^>]*>([^<]+)', html_content)
    if release_date_match:
        params['上市日期'] = release_date_match.group(1).strip()
        logger.info(f"正则找到上市日期: {params['上市日期']}")
    
    # 查找出厂系统内核
    os_match = re.search(r'出厂系统内核[^<]*<[^>]*>([^<]+)', html_content)
    if os_match:
        params['出厂系统内核'] = os_match.group(1).strip()
        logger.info(f"正则找到出厂系统内核: {params['出厂系统内核']}")
    
    # 查找操作系统
    vendor_os_match = re.search(r'操作系统[^<]*<[^>]*>([^<]+)', html_content)
    if vendor_os_match:
        params['操作系统'] = vendor_os_match.group(1).strip()
        logger.info(f"正则找到操作系统: {params['操作系统']}")
    
    return params

def test_url_for_parameters(url):
    """测试特定URL是否包含可提取的参数"""
    logger.info(f"\n===== 测试URL: {url} ====")
    
    try:
        # 发送请求获取页面内容
        response = requests.get(url, headers=headers, timeout=10)
        
        # 尝试多种编码方式解码内容
        html_content, encoding = try_decode_content(response.content)
        logger.info(f"页面使用编码: {encoding}")
        
        if response.status_code == 200:
            logger.info("成功获取页面内容")
            
            # 提取参数
            params = extract_parameters_from_html(html_content, url)
            
            # 打印提取结果
            logger.info("\n===== 此URL提取结果 =====")
            if params:
                for key, value in params.items():
                    logger.info(f"{key}: {value}")
                return params, True
            else:
                logger.warning("此URL未能提取到任何参数")
                return {}, False
        else:
            logger.error(f"请求失败，状态码: {response.status_code}")
            return {}, False
    except Exception as e:
        logger.error(f"发生错误: {e}")
        return {}, False

def main():
    logger.info(f"开始测试参数提取")
    
    # 首先测试主要的产品页面
    main_params, main_has_params = test_url_for_parameters(TEST_URL)
    
    # 如果主要页面没有参数，测试所有可能的参数页面URL
    if not main_has_params:
        logger.info("\n===== 主页面未找到参数，尝试其他参数页面URL ====")
        
        for url in PARAM_URLS:
            params, has_params = test_url_for_parameters(url)
            if has_params:
                logger.info(f"\n成功在URL: {url} 中找到参数！")
                break
    
    # 总结
    logger.info("\n===== 最终总结 =====")
    if main_has_params:
        logger.info("在主页面找到参数。")
    else:
        logger.warning("未能在任何测试的URL中找到参数。这可能意味着：")
        logger.warning("1. 网站使用JavaScript动态加载参数内容")
        logger.warning("2. 需要使用Selenium等工具模拟浏览器行为")
        logger.warning("3. 参数页面的URL格式与我们尝试的不同")
        logger.warning("4. 网站可能有反爬虫机制")

if __name__ == "__main__":
    main()