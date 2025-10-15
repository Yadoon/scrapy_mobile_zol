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

    def process_item(self, item, spider):

        # print(dict(item))
        res_data_select = self.data_select(item['phone_info_url'])
        if self.data_update_price(phone_info_url=item['phone_info_url'], phone_price=item['phone_price']):
            print('更新价格')
        else:
            if not res_data_select:
                print("增量数据")
                # print(res_data_select)
                # 增量数据
                self.data_insert(phone_name=item['phone_name'], phone_price=item['phone_price'],
                                 phone_info_url=item['phone_info_url'], phone_parameter_url=item['phone_parameter_url'],
                                 phone_x=item['phone_x'], phone_y=item['phone_y'], phone_size=item['phone_size'],
                                 phone_info=item['phone_info'], phone_brand=item['phone_brand'],
                                 os=item['os'], vendor_os=item['vendor_os'], release_date=item['release_date'],
                                 cpu_model=item['cpu_model'], gpu_model=item['gpu_model'])
                # self.data_insert(dict(item))
        # self.cursor.execute(insert_sql)
        # # 提交，不进行提交无法保存到数据库
        # self.conn.commit()

        return item

    def close_spider(self, spider):
        # 关闭游标和连接
        self.cursor.close()
        self.conn.close()