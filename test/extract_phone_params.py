import requests
from lxml import etree

# 读取本地HTML文件
def extract_params_from_html():
    try:
        # 尝试使用不同编码读取文件
        try:
            with open('param.shtml', 'r', encoding='utf-8') as f:
                html_content = f.read()
        except UnicodeDecodeError:
            try:
                with open('param.shtml', 'r', encoding='gbk', errors='replace') as f:
                    html_content = f.read()
            except:
                with open('param.shtml', 'r', encoding='latin-1') as f:
                    html_content = f.read()
            
        # 解析HTML
        tree = etree.HTML(html_content)
        
        # 初始化结果字典
        phone_params = {}
        
        # 提取上市日期（这里是问题所在！文本在th内的span标签中，不是直接在th标签中）
        # 错误的XPath: //th[normalize-space(.)="上市日期"]/following-sibling::td/span/text()
        # 正确的XPath: //th[span[normalize-space(.)="上市日期"]]/following-sibling::td/span/text()
        release_date = tree.xpath('//th[span[normalize-space(.)="上市日期"]]/following-sibling::td/span/text()')
        phone_params['release_date'] = release_date[0] if release_date else '未找到'
        
        # 提取出厂系统内核
        os = tree.xpath('//th[span[normalize-space(.)="出厂系统内核"]]/following-sibling::td/span/text()')
        phone_params['os'] = os[0] if os else '未找到'
        
        # 提取操作系统
        vendor_os = tree.xpath('//th[span[normalize-space(.)="操作系统"]]/following-sibling::td/span/text()')
        phone_params['vendor_os'] = vendor_os[0] if vendor_os else '未找到'
        
        # 为了验证，也可以提取其他参数
        cpu_model = tree.xpath('//th[span[normalize-space(.)="CPU型号"]]/following-sibling::td/span/text()')
        phone_params['cpu_model'] = cpu_model[0].split('<')[0] if cpu_model else '未找到'
        
        return phone_params
        
    except Exception as e:
        print(f"提取参数时出错: {e}")
        return {}

# 执行提取并打印结果
if __name__ == "__main__":
    params = extract_params_from_html()
    print("提取的手机参数:")
    for key, value in params.items():
        print(f"{key}: {value}")
        
    print("\n问题分析:")
    print("1. 原XPath无法匹配的原因: 文本内容实际在th标签内的span标签中，而不是直接在th标签中")
    print('2. 错误XPath格式: //th[normalize-space(.)="参数名"]/following-sibling::td/span/text()')
    print('3. 正确XPath格式: //th[span[normalize-space(.)="参数名"]]/following-sibling::td/span/text()')