import json

import mysql.connector
import datetime


class DBOperations:
    def __init__(self, db_host, db_port, db_user, db_password, db_name="fuckciscoexam"):
        self.db_host = db_host
        self.db_port = db_port
        self.db_user = db_user
        self.db_password = db_password
        self.db_name = db_name
        self.connection = self.connect_to_db()

    def connect_to_db(self):
        """
        连接数据库
        :return:
        """
        connection = mysql.connector.connect(
            host=self.db_host,
            port=self.db_port,
            user=self.db_user,
            password=self.db_password,
            database=self.db_name
        )
        return connection

    def authenticate_user(self, user_hash):
        """
        查询用户的信息是否正确
        :param user_hash:
        :return:
        """
        cursor = self.connection.cursor()
        cursor.execute(f"SELECT * FROM users WHERE user_hash='{user_hash}'")
        result = cursor.fetchone()
        cursor.close()
        return result is not None

    def is_question_exist(self, question):
        """
        验证问题是否存在
        :return:
        """
        cursor = self.connection.cursor(buffered=True)

        cursor.execute(f"SELECT * FROM exam_data WHERE question='{question}'")
        result = cursor.fetchone()
        cursor.close()

        return result is not None

    def add_item(self, item):
        """
        向题库中添加题目
        :param item:
        :return:
        """
        cursor = self.connection.cursor()
        query = f"INSERT INTO exam_data (status, course_name,question_type,question,options,right_answer,wrong_answer) VALUES (%s,%s,%s,%s,%s,%s,%s)"
        values = (item["status"], item["course_name"], item["question_type"], str(item["question"]), str(item["options"]), str(item["right_answer"]), str(item["wrong_answer"]))
        cursor.execute(query, values)
        self.connection.commit()
        cursor.close()

    def update_questions(self, question, status, right_answer):
        """
        更新某个问题的正确答案和状态
        :param right_answer:
        :param question:
        :param status:
        :return:
        """
        cursor = self.connection.cursor()
        query = f"update exam_data set status=%s,right_answer=%s where question=%s"
        values = (status, str(right_answer), question)
        cursor.execute(query, values)
        self.connection.commit()
        cursor.close()

    def clear_buf(self, serial_num):
        cursor = self.connection.cursor()
        command = f"delete from question_buf where serial_num='{serial_num}'"
        cursor.execute(command)
        self.connection.commit()
        cursor.close()

    def merge(self, serial_num):
        """
        将缓冲区merge到题库
        :return:
        """
        cursor = self.connection.cursor()
        query = f"INSERT INTO exam_data (status, course_name,question_type,question,options,right_answer,wrong_answer) select status,course_name,question_type,question,options,right_answer,wrong_answer from question_buf where status='pass' and serial_num='{serial_num}'"
        cursor.execute(query)
        self.connection.commit()
        cursor.close()

    def update_questions_to_buf(self, question, status, serial_num):
        """
        更新某个问题的正确答案和状态
        :param serial_num:
        :param right_answer:
        :param question:
        :param status:
        :return:
        """
        cursor = self.connection.cursor()
        query = f"update question_buf set status=%s where question=%s and serial_num=%s"
        values = (status, question, serial_num)
        cursor.execute(query, values)
        self.connection.commit()
        cursor.close()

    def update_questions_to_buf(self, question, status, right_answer, serial_num):
        """
        更新某个问题的正确答案和状态
        :param serial_num:
        :param right_answer:
        :param question:
        :param status:
        :return:
        """
        cursor = self.connection.cursor()
        query = f"update question_buf set status=%s,right_answer=%s where question=%s and serial_num=%s"
        values = (status, str(right_answer), question, serial_num)
        cursor.execute(query, values)
        self.connection.commit()
        cursor.close()

    def get_match_result(self, question):
        """
        根据问题进行匹配
        :return:
        """
        cursor = self.connection.cursor(buffered=True)
        query = f"SELECT * FROM exam_data WHERE question=%s and status=%s"
        values = (question,'pass')
        cursor.execute(query,values)
        rst = cursor.fetchone()
        cursor.close()
        return eval(rst[6]) if rst is not None else None

    def is_question_exist_in_buf(self, question, serial_num):
        """
        验证问题是否存在于缓冲区
        :return:
        """
        cursor = self.connection.cursor()

        cursor.execute(f"SELECT * FROM question_buf WHERE question='{question}' and serial_num='{serial_num}'")
        result = cursor.fetchone()
        cursor.close()

        return result is not None

    def get_status(self, question):
        """
        获取某个问题的状态
        :param question:
        :return:
        """
        cursor = self.connection.cursor()

        cursor.execute(f"SELECT * FROM exam_data WHERE question='{question}'")
        result = cursor.fetchone()
        cursor.close()

        return result[1]

    def add_item_to_buf(self, item, serial_num):
        cursor = self.connection.cursor()
        info = f"INSERT INTO question_buf (serial_num,status, course_name,question_type,question,options,right_answer,wrong_answer) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
        values = (serial_num, item["status"], item["course_name"], item["question_type"], str(item["question"]), str(item["options"]), str(item["right_answer"]), str(item["wrong_answer"]))
        cursor.execute(info, values)
        self.connection.commit()
        cursor.close()

    def get_questions(self, course_name):
        """
        获取对应课程的题库
        :return:
        """
        cursor = self.connection.cursor()
        cursor.execute(f"SELECT * FROM exam_data WHERE course_name='{course_name}'")
        result0 = cursor.fetchall()
        cursor.close()
        rst = []
        for r in result0:
            r = list(r)
            r[5] = eval(r[5])
            r[6] = eval(r[6])
            r[7] = eval(r[7])
            rst.append(r)
        return rst

    def get_num(self):
        """获取题目数目"""
        cursor = self.connection.cursor()
        # cursor.execute(f"select count(*) from exam_data where status='pass'")
        cursor.execute(f"select count(*) from exam_data")
        rst = cursor.fetchone()
        return rst[0]


if __name__ == '__main__':
    d = DBOperations("cd.acdawn.cn", 3306, "q", "y")
    print(d.get_num())
