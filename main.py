from selenium.webdriver import Chrome
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import logging

from db_operations import DBOperations
import wmi
import re

# chrome.exe --remote-debugging-port=9222 --user-data-dir="D:/selenium_test"
f = "%(asctime)s------>%(message)s"
logging.basicConfig(level=logging.INFO, format=f)
# 这个列表中的问题有问题，详见readme
ignore_question_list = [
    '请参见图示。显示的是什么类型的布线？'
]


def card_question_format(s):
    """
    将连线题的问题进行格式化
    :param s:
    :return:
    """
    obj_left = re.compile(r'.*?<span(.*?)>.*?')
    span_left = obj_left.findall(s)[0]
    return s.replace(f"<span{span_left}>", "").replace("</span>", "")


def get_serial_num():
    """
    根据每个用户的cpu序列号生成唯一的缓冲区
    :return:
    """
    c = wmi.WMI()
    for cpu in c.Win32_Processor():
        return cpu.ProcessorId.strip()


class Main:
    def __init__(self):
        self.course_title = None  # 课程名称
        self.lessons = None  # 课程列表
        self.options = Options()
        self.options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        self.wd = Chrome(service=Service('chromedriver.exe'), options=self.options)
        self.wd.implicitly_wait(3)
        self.db = DBOperations("cd.acdawn.cn", 3306, "q", "y")

    def get_exam_title(self, page):
        """
        获取exam标题
        :return:
        """
        if page == '试题反馈报告':
            title = self.wd.find_element(By.CSS_SELECTOR, 'h1')
        else:
            title = self.wd.find_element(By.CSS_SELECTOR, 'div.course-name')

        self.course_title = "".join(title.get_attribute("innerText").split("-")[1:]).strip()
        return "".join(title.get_attribute("innerText").split("-")[1:]).strip()

    def adjust(self):
        """
        对缓冲区中的题目进行校验，同时更新题库
        :return:
        """
        serial_num = get_serial_num()
        self.switch_window("试题反馈报告")
        title = self.get_exam_title("试题反馈报告")
        # 将缓冲区中的错题设置为not_pass
        wrong_fieldset = self.wd.find_elements(By.CSS_SELECTOR, 'h2[role="heading"] .material-text')
        logging.info(f"发现{len(wrong_fieldset)}个单选/多选错题")
        for field_index in range(len(wrong_fieldset)):
            wrong_fieldset = self.wd.find_elements(By.CSS_SELECTOR, 'h2[role="heading"] .material-text')
            wrong_question = wrong_fieldset[field_index].get_attribute("innerText").replace(" ", "").replace("\n", "")
            logging.info("设置错题状态为not_pass...")
            self.db.update_questions_to_buf(status='not_pass', question=wrong_question, right_answer=str([]), serial_num=serial_num)
        # 接下来处理连线题
        question_card_ele = self.wd.find_elements(By.CSS_SELECTOR, '.DndContainer .label-container h5 p')
        for question_card_ele_index in range(len(question_card_ele)):
            question_card_ele = self.wd.find_elements(By.CSS_SELECTOR, '.DndContainer .label-container h5 p')
            question = card_question_format(question_card_ele[question_card_ele_index].get_property("innerHTML").replace(" ", "").replace("\n", ""))
            logging.info("设置错题状态为not_pass...")
            self.db.update_questions_to_buf(status='not_pass', question=question, right_answer=str([]), serial_num=serial_num)
        # 将缓冲区中pass的题目加入到题库
        self.db.merge(serial_num)
        logging.info(f"已对题库{title}进行更新......")
        self.db.clear_buf(serial_num)
        logging.info(f"已清空缓冲区......")

    def merge(self):
        """
        将缓冲区所有数据合并到题库
        :return:
        """
        serial_num = get_serial_num()
        self.db.merge(serial_num)
        logging.info("已将缓冲区合并到题库...")
        logging.info(f"已清空缓冲区......")
        self.db.clear_buf(serial_num)

    def switch_window(self, window_name):
        # 切换到当前窗口
        all_windows = self.wd.window_handles
        for window in all_windows:
            self.wd.switch_to.window(window)
            if self.wd.title == window_name:
                break

    def read_exam_result(self):
        """
        做题完毕后进行读取你做的题目,首先放到你的缓冲区
        :return:
        """
        # 找到序列号
        serial_num = get_serial_num()
        # 切换到当前窗口
        self.switch_window("参加考试")
        title = self.get_exam_title("参加考试")
        # 对所有fieldset遍历
        fieldset = self.wd.find_elements(By.CSS_SELECTOR, '.questionFieldset')
        for field_index in range(len(fieldset)):
            # 刷新fieldset
            fieldset = self.wd.find_elements(By.CSS_SELECTOR, '.questionFieldset')
            # 找到问题类型
            question_type_ele = fieldset[field_index].find_element(By.CSS_SELECTOR, 'input')
            question_type = question_type_ele.get_attribute("type")
            # 找到当前问题内容
            question_ele = fieldset[field_index].find_element(By.CSS_SELECTOR, '.mattext')
            question = question_ele.get_attribute("innerText").replace(" ", "").replace("\n", "")
            # 获取当前fieldset的所有选项
            options = []
            options_ele = fieldset[field_index].find_elements(By.CSS_SELECTOR, '.ai-option-label')
            right_answer = []
            for option_index in range(len(options_ele)):
                # 刷新元素
                options_ele = fieldset[field_index].find_elements(By.CSS_SELECTOR, '.ai-option-label')
                option_content = options_ele[option_index].get_attribute("innerText").replace(" ", "").replace("\n", "")
                if question_type == "radio":
                    if options_ele[option_index].find_element(By.CSS_SELECTOR, 'input').get_attribute("data-radio-is-checked") == "true":
                        right_answer.append(option_content)
                elif question_type == "checkbox":
                    if options_ele[option_index].find_element(By.CSS_SELECTOR, 'input').get_attribute("checked") == "true":
                        right_answer.append(option_content)
                options.append(option_content)
            tmp_field = {
                "status": "pass",
                "course_name": title,
                "question_type": question_type,  # 问题类型
                "question": question,  # 问题内容
                "options": options,  # 选项
                "right_answer": right_answer,  # 正确答案
                "wrong_answer": []  # 错误答案
            }
            # 数据库部分处理
            if question in ignore_question_list:
                continue
            if self.db.is_question_exist(question):
                continue
            # 若缓冲区不存在题库就放到缓冲区中
            if not self.db.is_question_exist_in_buf(question, serial_num):
                self.db.add_item_to_buf(tmp_field, serial_num)
                logging.info("发现新题目...加入缓冲区...success")
        # self.read_card(title, serial_num)

    def write_exam(self):
        """
        从题库中搜索答案，自动答题
        :return:
        """
        # 加载题库
        # 切换到当前窗口
        self.switch_window("参加考试")
        # 首先要点击两遍所有题目
        ques_num = self.wd.find_elements(By.CSS_SELECTOR, '.questionbartable li button')
        ques_num[0].click()
        for i in range(len(ques_num) - 1):
            self.wd.find_element(By.ID, "next").click()
        # 对所有fieldset遍历
        num_matched = 0
        fieldset = self.wd.find_elements(By.CSS_SELECTOR, '.questionFieldset')
        for field_index in range(len(fieldset)):
            # 接下来聚焦于每一道题
            # 刷新fieldset
            fieldset = self.wd.find_elements(By.CSS_SELECTOR, '.questionFieldset')
            # 找到当前问题内容
            question_ele = fieldset[field_index].find_element(By.CSS_SELECTOR, '.mattext')
            question = question_ele.get_attribute("innerText").replace(" ", "").replace("\n", "")
            # 搜索题库:
            logging.info(f"正在匹配题目{field_index}...")
            match_rst = self.db.get_match_result(question)
            if match_rst is not None:
                logging.info(f"匹配题目{field_index}成功...")
                num_matched += 1
                # 当前题目选项们
                options_ele = fieldset[field_index].find_elements(By.CSS_SELECTOR, '.ai-option-label')
                for option_index in range(len(options_ele)):
                    # 接下来之只看每一个小选项
                    # 刷新元素
                    options_ele = fieldset[field_index].find_elements(By.CSS_SELECTOR, '.ai-option-label')
                    # 选项内容
                    option_content = options_ele[option_index].get_attribute("innerText").replace(" ", "").replace("\n", "")
                    click_btn = options_ele[option_index].find_element(By.CSS_SELECTOR, 'input')
                    # 若选项是正确答案
                    if option_content in match_rst:
                        if not click_btn.is_selected():
                            self.wd.execute_script("arguments[0].click();", click_btn)
                    # 若选项不是正确答案
                    else:
                        if click_btn.is_selected():
                            self.wd.execute_script("arguments[0].click();", click_btn)
        # 接下来操作连线题目
        # 最后也要点击一遍所有题目来刷新
        ques_num = self.wd.find_elements(By.CSS_SELECTOR, '.questionbartable li button')
        ques_num[0].click()
        for i in range(len(ques_num) - 1):
            self.wd.find_element(By.ID, "next").click()
        logging.info(f"成功在题库中匹配到{num_matched}个单选/多选题目，已自动完成......")
        # self.write_card() 待优化

    def hold_and_drop(self, src, dest):
        """
        连线题自动拖拽元素
        :param src:
        :param dest:
        :return:
        """
        java_script = "var args = arguments," + "callback = args[args.length - 1]," + "source = args[0]," + "target = args[1]," + "offsetX = (args.length > 2 && args[2]) || 0," + "offsetY = (args.length > 3 && args[3]) || 0," + "delay = (args.length > 4 && args[4]) || 1;" + "if (!source.draggable) throw new Error('Source element is not draggable.');" + "var doc = source.ownerDocument," + "win = doc.defaultView," + "rect1 = source.getBoundingClientRect()," + "rect2 = target ? target.getBoundingClientRect() : rect1," + "x = rect1.left + (rect1.width >> 1)," + "y = rect1.top + (rect1.height >> 1)," + "x2 = rect2.left + (rect2.width >> 1) + offsetX," + "y2 = rect2.top + (rect2.height >> 1) + offsetY," + "dataTransfer = Object.create(Object.prototype, {" + "  _items: { value: { } }," + "  effectAllowed: { value: 'all', writable: true }," + "  dropEffect: { value: 'move', writable: true }," + "  files: { get: function () { return undefined } }," + "  types: { get: function () { return Object.keys(this._items) } }," + "  setData: { value: function (format, data) { this._items[format] = data } }," + "  getData: { value: function (format) { return this._items[format] } }," + "  clearData: { value: function (format) { delete this._items[format] } }," + "  setDragImage: { value: function () { } }" + "});" + "target = doc.elementFromPoint(x2, y2);" + "if(!target) throw new Error('The target element is not interactable and need to be scrolled into the view.');" + "rect2 = target.getBoundingClientRect();" + "emit(source, 'dragstart', delay, function () {" + "var rect3 = target.getBoundingClientRect();" + "x = rect3.left + x2 - rect2.left;" + "y = rect3.top + y2 - rect2.top;" + "emit(target, 'dragenter', 1, function () {" + "  emit(target, 'dragover', delay, function () {" + "\ttarget = doc.elementFromPoint(x, y);" + "\temit(target, 'drop', 1, function () {" + "\t  emit(source, 'dragend', 1, callback);" + "});});});});" + "function emit(element, type, delay, callback) {" + "var event = doc.createEvent('DragEvent');" + "event.initMouseEvent(type, true, true, win, 0, 0, 0, x, y, false, false, false, false, 0, null);" + "Object.defineProperty(event, 'dataTransfer', { get: function () { return dataTransfer } });" + "element.dispatchEvent(event);" + "win.setTimeout(callback, delay);" + "}"
        self.wd.execute_script(java_script, src, dest, 12, 12, 122)  # 点击课程

    def write_card(self):
        """
        自动写连线题
        :return:
        """
        self.switch_window("参加考试")
        card_set = self.wd.find_elements(By.CSS_SELECTOR, '.DndContainer')
        for card_index in range(len(card_set)):
            # 接下来聚焦于每一道连线题
            # 刷新fieldset
            card_set = self.wd.find_elements(By.CSS_SELECTOR, '.DndContainer')
            # 找到当前问题内容
            card_ele = card_set[card_index].find_element(By.CSS_SELECTOR, '.label-container h5 span')
            question = card_ele.get_attribute("innerText").replace(" ", "").replace("\n", "")
            # 搜索题库:
            logging.info(f"正在匹配题目{card_index}...")
            match_rst = self.db.get_match_result(question)
            if match_rst is not None:
                logging.info("匹配成功...")
                print(question, end="-->")
                print(match_rst)
                for match in match_rst:
                    item = match.split('-')
                    card_set = self.wd.find_elements(By.CSS_SELECTOR, '.DndContainer')
                    src = card_set[card_index].find_elements(By.CSS_SELECTOR, '.options-list div[role="listitem"]')[0]
                    dest = card_set[card_index].find_elements(By.CSS_SELECTOR, '.drop-col div[role="listitem"]')[int(item[1])]
                    self.hold_and_drop(src, dest)

    def read_card(self, title, serial_num):
        """
        读取你写的连线题到缓冲区
        """
        # 对所有fieldset遍历
        card_set = self.wd.find_elements(By.CSS_SELECTOR, '.DndContainer')
        for card_index in range(len(card_set)):
            card_set = self.wd.find_elements(By.CSS_SELECTOR, '.DndContainer')
            # 问题类型
            question_type = "matching"
            # 找到当前题目
            question_ele = card_set[card_index].find_element(By.CSS_SELECTOR, '.label-container h5 p')
            question = card_question_format(question_ele.get_property("innerHTML").replace(" ", "").replace("\n", ""))
            # 获取当前card_set左侧的所有选项
            options = []
            options_ele = card_set[card_index].find_elements(By.CSS_SELECTOR, '.no-gutters .nodrag')
            for option_index in range(len(options_ele)):
                options_ele = card_set[card_index].find_elements(By.CSS_SELECTOR, '.no-gutters .nodrag')
                options.append(options_ele[option_index].get_attribute("innerText"))
            # 对右侧内容遍历
            right_answer = []
            options_r_ele = card_set[card_index].find_elements(By.CSS_SELECTOR, '.drop-zone')
            for options_r_index in range(len(options_r_ele)):
                options_r_ele = card_set[card_index].find_elements(By.CSS_SELECTOR, '.drop-zone')
                cur_opt_r = options_r_ele[options_r_index].find_element(By.XPATH, 'div/div')
                if cur_opt_r.get_attribute("class") == 'drag-option':
                    cur_opt_r = options_r_ele[options_r_index].find_element(By.XPATH, 'div/div')
                    # 右侧的答案
                    tmp = cur_opt_r.find_element(By.CSS_SELECTOR, 'p span').get_attribute("innerText")
                    # 右侧答案对应的索引
                    options.index(tmp)
                    right_answer.append(f'{options.index(tmp)}-{options_r_index}')
            # 对right_answer进行排序，不然后面没办法写题
            right_answer.sort()
            tmp_field = {
                "status": "pass",
                "course_name": title,
                "question_type": question_type,  # 问题类型
                "question": question,  # 问题内容
                "options": options,  # 选项
                "right_answer": right_answer,  # 正确答案
                "wrong_answer": []  # 错误答案
            }
            # 数据库部分处理
            # 若缓冲区不存在题目就放到缓冲区中
            if not self.db.is_question_exist_in_buf(question, serial_num):
                self.db.add_item_to_buf(tmp_field, serial_num)
                logging.info("发现新的连线题目...加入缓冲区...success")
            else:
                # 存在题目则更新正确选项
                self.db.update_questions_to_buf(question, "pass", right_answer, serial_num)


if __name__ == '__main__':
    print("1:刚打开一套新的题(将匹配题库自动填写)")
    print("2:刚写完题目(即将把写好的题目读入数据库)")
    print("3:在核对题目(在试题反馈页面更新题库信息)")
    print("4:若题目全对,则执行此选项,否则执行选项3")
    option = int(input("请输入选择当前场景:"))
    m = Main()
    if option == 1:
        m.write_exam()
    elif option == 2:
        m.read_exam_result()
    elif option == 3:
        m.adjust()
    elif option == 4:
        m.merge()
