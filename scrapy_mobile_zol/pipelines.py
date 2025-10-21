# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html
import pymysql
from twisted.internet import task


class ScrapyMobileZolPipeline(object):
    def __init__(self):
        # 建立连接
        self.conn = pymysql.connect(
            host='10.225.137.189',
            port=13306,
            user='root',
            password='Dobest2022!',
            db='cloud_test_dev_0814',
            charset='utf8'
        )

        # 创建游标
        self.cursor = self.conn.cursor()
        self.looping_call = task.LoopingCall(self.heartbeat_query)
        self.looping_call.start(1.0)  # 每1秒执行一次

    def heartbeat_query(self):
        """心跳查询，保持连接活跃"""
        try:
            self.conn.ping(reconnect=True)
            # 执行简单的查询保持连接
            self.cursor.execute("SELECT 1")
            result = self.cursor.fetchone()
            print(f"Heartbeat query result: {result}")
        except Exception as e:
            print(f"Heartbeat query error: {e}")

    # def data_insert(self, phone_name, phone_price, phone_info_url, phone_parameter_url, phone_x, phone_y, phone_size, phone_info, phone_brand):
    def data_insert(self, **kwargs):
        try:
            # 在执行任何操作前，检查并重连
            self.conn.ping(reconnect=True)
            insert_sql = """
                    insert into spider_mobile_zol(
                    phone_name,
                    phone_price,
                    phone_info_url,
                    phone_parameter_url,
                    phone_x,
                    phone_y,
                    phone_size,
                    phone_info,
                    phone_brand,
                    os,
                    vendor_os,
                    release_date,
                    cpu_model,
                    gpu_model) 
                    VALUES("{}","{}","{}","{}",{},{},{},"{}","{}","{}","{}","{}","{}","{}")
                    """.format(kwargs['phone_name'],
                               kwargs['phone_price'],
                               kwargs['phone_info_url'],
                               kwargs['phone_parameter_url'],
                               kwargs['phone_x'],
                               kwargs['phone_y'],
                               kwargs['phone_size'],
                               kwargs['phone_info'],
                               kwargs['phone_brand'],
                               kwargs['os'],
                               kwargs['vendor_os'],
                               kwargs['release_date'],
                               kwargs['cpu_model'],
                               kwargs['gpu_model'])
            # 执行插入数据到数据库操作
            # print(insert_sql)
            self.cursor.execute(insert_sql)
            # 提交，不进行提交无法保存到数据库
            self.conn.commit()
        except Exception as e:
            print(f"数据库插入错误: {e}")
            self.conn.rollback()

    def data_select(self, phone_info_url):
        select_sql = "SELECT * FROM spider_mobile_zol WHERE phone_info_url = '{}' and phone_price > 0".format(phone_info_url)
        self.cursor.execute(select_sql)
        res = self.cursor.fetchone()
        # print("res = ", res)
        return res

    def data_update_price(self, phone_info_url, phone_price):
        select_sql = "SELECT * FROM spider_mobile_zol WHERE phone_info_url = '{}' and phone_price = 0".format(
            phone_info_url)
        self.cursor.execute(select_sql)
        res = self.cursor.fetchone()
        # print("res = ", res)
        if res:
            uplate_sql = "UPDATE spider_mobile_zol SET phone_price={} WHERE phone_info_url = '{}' and phone_price = 0".format(phone_price, phone_info_url)

            # print(uplate_sql)
            self.cursor.execute(uplate_sql)
            self.conn.commit()
            return True
        else:
            return False
            
    def data_update_all(self, item):
        """更新数据库中的所有字段"""
        try:
            # 在执行任何操作前，检查并重连
            self.conn.ping(reconnect=True)
            update_sql = """
                UPDATE spider_mobile_zol 
                SET phone_name=%s,
                    phone_price=%s,
                    phone_parameter_url=%s,
                    phone_x=%s,
                    phone_y=%s,
                    phone_size=%s,
                    phone_info=%s,
                    phone_brand=%s,
                    os=%s,
                    vendor_os=%s,
                    release_date=%s,
                    cpu_model=%s,
                    gpu_model=%s 
                WHERE phone_info_url=%s
            """
            
            # 使用参数化查询以避免SQL注入
            params = (
                item['phone_name'],
                item['phone_price'],
                item['phone_parameter_url'],
                item['phone_x'],
                item['phone_y'],
                item['phone_size'],
                item['phone_info'],
                item['phone_brand'],
                item['os'],
                item['vendor_os'],
                item['release_date'],
                item['cpu_model'],
                item['gpu_model'],
                item['phone_info_url']
            )
            
            self.cursor.execute(update_sql, params)
            self.conn.commit()
            print(f"已更新手机数据: {item['phone_name']}")
            return True
        except Exception as e:
            print(f"数据库更新错误: {e}")
            self.conn.rollback()
            return False

    def process_item(self, item, spider):

        # print(dict(item))
        res_data_select = self.data_select(item['phone_info_url'])
        
        # 确保所有必要的字段都有默认值
        if 'phone_parameter_url' not in item:
            item['phone_parameter_url'] = ''
        if 'phone_x' not in item or item['phone_x'] is None:
            item['phone_x'] = 0
        if 'phone_y' not in item or item['phone_y'] is None:
            item['phone_y'] = 0
        if 'phone_size' not in item or item['phone_size'] is None:
            item['phone_size'] = 0.0
        if 'phone_info' not in item:
            item['phone_info'] = ''
        if 'phone_brand' not in item:
            item['phone_brand'] = ''
        if 'os' not in item:
            item['os'] = ''
        if 'vendor_os' not in item:
            item['vendor_os'] = ''
        if 'release_date' not in item:
            item['release_date'] = ''
        if 'cpu_model' not in item:
            item['cpu_model'] = ''
        if 'gpu_model' not in item:
            item['gpu_model'] = ''
        
        # 如果记录存在，更新所有字段
        if res_data_select:
            self.data_update_all(item)
        else:
            # 如果记录不存在，执行插入操作
            print("增量数据")
            self.data_insert(phone_name=item['phone_name'], phone_price=item['phone_price'],
                             phone_info_url=item['phone_info_url'], phone_parameter_url=item['phone_parameter_url'],
                             phone_x=item['phone_x'], phone_y=item['phone_y'], phone_size=item['phone_size'],
                             phone_info=item['phone_info'], phone_brand=item['phone_brand'],
                             os=item['os'], vendor_os=item['vendor_os'], release_date=item['release_date'],
                             cpu_model=item['cpu_model'], gpu_model=item['gpu_model'])

        return item

    def close_spider(self, spider):
        # 关闭游标和连接
        self.cursor.close()
        self.conn.close()