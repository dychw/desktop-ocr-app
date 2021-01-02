Desktop OCR App - デスクトップOCRアプリ

# ToDo
[]  認識精度
[]  処理速度
[x] partial screen capture(範囲選択)

# 動作確認した環境
macOS 10.15.7

# wxPython
参考:
- [pythonとOCRでyoutube広告自動スキップツール作成](https://qiita.com/chuntaweb/items/998ec0da7988a860c747)
- [wxPythonでスレッドを使ってみる](https://bty.sakura.ne.jp/wp/archives/626)

# pytesseract
## INSTALLATION
参考: https://tesseract-ocr.github.io/tessdoc/Installation.html
```shell
$ brew install tesseract

$ pip3 install Pillow
$ pip3 install pytesseract
```
動作確認
```shell
$ tesseract test.jpg  out 
```

```python
import pytesseract
from PIL import Image

print(pytesseract.get_languages(config=''))
# ['eng', 'osd', 'snum']
print(pytesseract.image_to_string(Image.open('en_test.jpg')))
```

## tesseractを日本語に対応させる
参考: [MacでTesseract OCRを使って画像内のテキストを取り出してみる](https://rooter.jp/ml/tesseract-with-mac/)
```

動作確認
```script
print(pytesseract.image_to_string(Image.open('jp_test.jpg'), lang='jpn'))
```