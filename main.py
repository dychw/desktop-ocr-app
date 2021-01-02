import wx
import wx.lib.newevent
import cv2
import threading
import traceback
import os
import sys
import time
import datetime

# 画面キャプチャ処理
from PIL import ImageGrab
from PIL import Image
import numpy as np

# OCR処理
import difflib
import pytesseract
import re

import pprint
pp = pprint.PrettyPrinter(indent=4, width=150)

# 新しいイベントクラスとイベントを定義する
(OcrUpdateEvent, EVT_MY_THREAD) = wx.lib.newevent.NewEvent()

"""
定数
"""
# 初期値 最小時間間隔(秒)
INIT_MIN_INTERVAL_TIME = 0.1

# 初期値 座標
INIT_ZAHYO = -1

# フレーム タイトル
FLAME_TITLE = 'OCR'

# フレーム 横幅
FLAME_WIDTH = 200

# フレーム 縦幅
FLAME_HEIGHT = 220

# ステータスボタン 横幅
STAT_BTN_WIDTH = 200

# ステータスボタン 縦幅
STAT_BTN_HEIGHT = 80

# ステータスボタン START 色
STAT_BTN_COLOR_START = '#00FF00'

# ステータスボタン STOPPING 色
STAT_BTN_COLOR_STOPPING = '#808080'

# ステータスボタン STOP 色
STAT_BTN_COLOR_STOP = '#FF0000'

# 設定ボタン 横幅
SETTING_BTN_WIDTH = 200

# 設定ボタン 縦幅
SETTING_BTN_HEIGHT = 40

# 画面キャプチャ画像 縦幅
CAPTURE_IMG_WIDTH = 800

# ステータス切り替え最小時間(秒)
MIN_TIME_STAT_CHANGE = 5

# OCRの対象となる言語
OCR_LANG = 'jpn'

"""
グローバル変数
"""
# 実行スレッド
exec_thread = None

# 設定値
setting_value = None


class SETTING_VALUE:
    """
    設定値
    """

    def __init__(self):
        # 停止フラグ
        self.flg_stop = True

        # 最小実行間隔(秒)
        self.min_interval_time = INIT_MIN_INTERVAL_TIME

        self.top = INIT_ZAHYO

        self.bottom = INIT_ZAHYO

        self.left = INIT_ZAHYO

        self.right = INIT_ZAHYO

        self.rate = 1

        # OCRの対象となる言語
        self.ocr_lang = OCR_LANG


class WINDOW_MAIN:
    def __init__(self, title, size_x, size_y):
        self.title = title
        self.size_x = size_x
        self.size_y = size_y

        self.frame = wx.Frame(None, wx.ID_ANY, title, size=(size_x, size_y))

        self.panel_root = wx.Panel(self.frame, wx.ID_ANY)

        # パネル ボタン
        self.panel_btn = PANEL_BTN(self.panel_root)

        # レイアウト設定
        layout_root = wx.BoxSizer(wx.VERTICAL)
        layout_root.Add(self.panel_btn, 0, wx.GROW | wx.BOTTOM | wx.TOP)
        self.panel_root.SetSizer(layout_root)
        layout_root.Fit(self.panel_root)

    def show(self):
        """
        表示
        """
        self.frame.Show()


class PANEL_BTN(wx.Panel):
    """
    パネル ボタン
    """

    def __init__(self, parent):
        super().__init__(parent, wx.ID_ANY)

        # ラベル
        self.label = wx.StaticText(self, wx.ID_ANY, 'OCR')
        font_label = wx.Font(14, wx.FONTFAMILY_DEFAULT,
                             wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.label.SetFont(font_label)

        # ステータスボタン
        self.stat_btn = wx.Button(self, wx.ID_ANY, 'EXECUTE', size=(
            STAT_BTN_WIDTH, STAT_BTN_HEIGHT))
        self.stat_btn.SetBackgroundColour(STAT_BTN_COLOR_START)
        self.stat_btn.Bind(wx.EVT_BUTTON, self.onclick_stat_btn)

        # ウインドウ設定ボタン
        self.window_btn = wx.Button(self, wx.ID_ANY, 'SETTING', size=(
            SETTING_BTN_WIDTH, SETTING_BTN_HEIGHT))
        self.window_btn.Bind(wx.EVT_BUTTON, self.onclick_window_btn)

        # OCRの出力結果
        self.text_disp = wx.TextCtrl(
            self, style=wx.TE_MULTILINE, size=(200, 400))
        self.Bind(EVT_MY_THREAD, self.on_update)

        # 描画中フラグ
        self.flg_drawing = False
        # 開始位置
        self.ix, self.iy = 0, 0

        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(self.label, flag=wx.EXPAND | wx.TOP |
                   wx.BOTTOM | wx.LEFT, border=5)
        layout.Add(self.stat_btn, flag=wx.EXPAND | wx.BOTTOM, border=5)
        layout.Add(self.window_btn, flag=wx.EXPAND | wx.BOTTOM, border=5)
        layout.Add(self.text_disp, flag=wx.EXPAND, border=5)

        self.SetSizer(layout)

    def onclick_stat_btn(self, event):
        """
        ステータスボタンクリック時処理
        """
        global setting_value

        if INIT_ZAHYO == setting_value.top:
            wx.MessageBox(
                'First select the area with the setting button.\n最初に設定ボタンで領域を選択してください', 'Error エラー')
            return

        if not setting_value.flg_stop:
            self.stat_btn.Disable()
            self.stat_btn.SetBackgroundColour(STAT_BTN_COLOR_STOPPING)
            self.stat_btn.SetLabel('EXECUTE')

            stop()

            time.sleep(MIN_TIME_STAT_CHANGE)
            self.stat_btn.SetBackgroundColour(STAT_BTN_COLOR_START)
            self.stat_btn.Enable()
        else:
            self.stat_btn.Disable()
            self.stat_btn.SetBackgroundColour(STAT_BTN_COLOR_STOPPING)
            self.stat_btn.SetLabel('STOP')

            start(self)

            time.sleep(MIN_TIME_STAT_CHANGE)
            self.stat_btn.SetBackgroundColour(STAT_BTN_COLOR_STOP)
            self.stat_btn.Enable()

    def onclick_window_btn(self, event):
        """
        ウインドウ設定ボタンクリック時処理
        """
        # 指定サイズの全画面キャプチャ画像取得
        self.img = self.get_capture_img(CAPTURE_IMG_WIDTH)

        # 表示用画像
        self.img_copy = None

        # window名設定
        cv2.namedWindow(winname='img')

        # マウスイベント設定
        cv2.setMouseCallback('img', self.draw_rectangle)

        # 画像表示
        cv2.imshow('img', self.img)

        wx.MessageBox('OCRの対象となる領域を選択してください', '領域選択')

    def draw_rectangle(self, event, x, y, flags, param):
        """
        四角形を描画
        """
        if event == cv2.EVENT_LBUTTONDOWN:
            self.flg_drawing = True
            self.ix, self.iy = x, y

        elif event == cv2.EVENT_MOUSEMOVE:
            if self.flg_drawing == True:
                self.img_copy = self.img.copy()
                self.img_copy = cv2.rectangle(
                    self.img_copy, (self.ix, self.iy), (x, y), (0, 0, 255), -1)
                cv2.imshow('img', self.img_copy)

        elif event == cv2.EVENT_LBUTTONUP:
            self.flg_drawing = False
            self.img_copy = cv2.rectangle(
                self.img_copy, (self.ix, self.iy), (x, y), (0, 0, 255), -1)
            cv2.imshow('img', self.img_copy)

        if event == cv2.EVENT_LBUTTONUP:
            global setting_value

            # 右に行くほど増加
            if self.ix < x:
                left = self.ix
                right = x
            else:
                left = x
                right = self.ix

            # 下に行くほど増加
            if self.iy < y:
                bottom = y
                top = self.iy
            else:
                bottom = self.iy
                top = y

            setting_value.top = top
            setting_value.bottom = bottom
            setting_value.left = left
            setting_value.right = right

            print(setting_value.top)
            print(setting_value.bottom)
            print(setting_value.left)
            print(setting_value.right)

    def on_update(self, evt):
        """
        OCRの出力を画面に反映する
        """
        self.text_disp.AppendText(evt.msg+'\n')

    def get_capture_img(self, width):
        """
        指定サイズの全画面キャプチャ画像取得
        """
        # 全画面キャプチャ画像取得
        img = ImageGrab.grab()
        orgWidth, orgHeight = img.size

        # レートを算出
        desktop_width = orgWidth
        rate = width / desktop_width

        global setting_value
        setting_value.rate = rate

        # リサイズ後のサイズを算出
        width_resized = int(width)
        height_resized = int(orgHeight * rate)

        # リサイズ
        img_resized = img.resize((width_resized, height_resized))
        cv_img = cv2.cvtColor(np.array(img_resized), cv2.COLOR_RGB2BGR)

        return cv_img


class auto_click_Thread(threading.Thread):
    def __init__(self, win):
        super(auto_click_Thread, self).__init__()

        # 呼び出し元が終了したらスレッドも終了するようデーモン化
        self.setDaemon(True)

        self.win = win
        self.blank_pattern = re.compile(r'[ \n\x0c]')

    def stop(self):
        global setting_value

        setting_value.flg_stop = True

    def run(self):
        global setting_value

        setting_value.flg_stop = False

        min_interval_time = setting_value.min_interval_time
        top = int(setting_value.top * (1 / setting_value.rate))
        bottom = int(setting_value.bottom * (1 / setting_value.rate))
        left = int(setting_value.left * (1 / setting_value.rate))
        right = int(setting_value.right * (1 / setting_value.rate))

        self.click_text(min_interval_time, top, bottom,
                        left, right, setting_value.ocr_lang)

    def click_text(self, min_interval_time, top, bottom, left, right, ocr_lang):
        global setting_value

        timer = TIMER(min_interval_time)
        previous_recognition = ""
        while True:
            if setting_value.flg_stop:
                break

            if timer.can_exec():
                img = ImageGrab.grab(bbox=(left, top, right, bottom))
                current_recognition = pytesseract.image_to_string(
                    img, lang=ocr_lang)
                blank_rate = len(re.findall(
                    self.blank_pattern, current_recognition)) / len(current_recognition)
                if blank_rate > 0.33:
                    continue

                similarity = difflib.SequenceMatcher(
                    None, current_recognition, previous_recognition).ratio()
                if similarity < 0.35:
                    evt = OcrUpdateEvent(msg=(previous_recognition))
                    wx.PostEvent(self.win, evt)
                    previous_recognition = current_recognition
                elif similarity > 0.6:
                    # 前に似た文字列を認識した場合、新しい文字列を記憶する。
                    previous_recognition = current_recognition

            time.sleep(0.1)


def start(win):
    global exec_thread
    global setting_value

    exec_thread = auto_click_Thread(win)
    exec_thread.start()


def stop():
    global exec_thread

    exec_thread.stop()


class TIMER:
    def __init__(self, min_interval_time):
        # 最小実行時間
        self.min_interval_time = datetime.timedelta(seconds=min_interval_time)

        # 最終実行時間
        self.last_exec_time = datetime.datetime.now()

    def can_exec(self):
        """
        時間の制限のため実行可能かを判定
        """
        interval_time = datetime.datetime.now() - self.last_exec_time

        if interval_time < self.min_interval_time:
            return False

        return True


if __name__ == '__main__':
    try:
        application = wx.App()

        setting_value = SETTING_VALUE()
        OCR_LANG

        window_main = WINDOW_MAIN(FLAME_TITLE, FLAME_WIDTH, FLAME_HEIGHT)
        window_main.show()

        application.MainLoop()
    except:
        wx.MessageBox(traceback.format_exc(), 'FatalError 致命的なエラー')

    sys.exit(0)
