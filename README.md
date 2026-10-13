# tepra-net-print

キングジム「テプラ」PRO のネットワークモデル（SR-R7900P / SR5900P）に、公式ドライバなしで Linux などから文字ラベルを印刷する Python スクリプトです。

Print text labels to KING JIM TEPRA PRO network label printers (SR-R7900P / SR5900P) over LAN, without the official Windows/macOS software.

> **非公式** です。キングジムとは無関係で、リバースエンジニアリングされたプロトコルを使っています。本体ファームウェアの更新で動かなくなる可能性があります。

## 必要なもの

- [uv](https://docs.astral.sh/uv/)、または Python 3.9 以上と [Pillow](https://pypi.org/project/Pillow/)
- CJK フォント（既定は `/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc`、環境変数 `TEPRA_FONT` で変更可）
- テプラと UDP/TCP 9100 番で通信できるネットワーク

## すぐ試す

クローンせずに、`curl` で取ってそのまま実行できます。[uv](https://docs.astral.sh/uv/) があれば Pillow も自動で用意されます。

```sh
curl -fsSL https://raw.githubusercontent.com/azishio/tepra-net-print/main/tepra.py | uv run - <PRINTER_IP> print "ラベル文字"
```

uv が無い場合は、Pillow を入れてから `python3` に渡します。

```sh
curl -fsSL https://raw.githubusercontent.com/azishio/tepra-net-print/main/tepra.py | python3 - <PRINTER_IP> print "ラベル文字"
```

## 使い方

```sh
# 状態（印刷中か、エラー、テープ幅）を表示
python3 tepra.py <PRINTER_IP> status

# preview.png だけ作って印刷しない
python3 tepra.py <PRINTER_IP> print "ラベル文字" --dry-run

# 印刷
python3 tepra.py <PRINTER_IP> print "ラベル文字"
```

テープ幅は本体から自動で読み取り、文字はその幅いっぱい（8 割）の 1 行で描きます。

## 動作確認

| 機種 | テープ | 結果 |
|---|---|---|
| SR-R7900P | 9mm | 印刷できた |

ほかのテープ幅は [hikalium/sr5900p](https://github.com/hikalium/sr5900p) の SR5900P 向けの値をそのまま使っており、SR-R7900P では未確認です。50mm テープは判別できません。

## プロトコル概要

1. UDP 9100 に `TPRT` で始まる 32 バイトのヘッダを送る（応答は `tprt`）。命令 1 = 状態、2 = 印刷開始、3 = 印刷終了。
2. 印刷開始の後にだけ TCP 9100 が開く。命令 `0x0101` → `0x0100` でデータ送信を通知する。
3. TCP で `ESC { 長さ 中身 チェックサム }` の設定命令、360dpi・1bpp のラスタを 1 列ずつ（`ESC . 00 00 00 01` + 高さ + ビット列）、終端 `0x0c` を送る。
4. 状態をポーリングして印刷終了を待ち、命令 3 を送る。

SR-R7900P と SR5900P の違い:

- 状態応答のペイロードが 78 バイト（SR5900P は 20 バイト）。先頭の項目の意味は同じ。
- `0x0100` への応答が `0x18`（SR5900P は `0x10`）。

## 謝辞

プロトコルは [hikalium/sr5900p](https://github.com/hikalium/sr5900p)（MIT）と、[Mine02C4/TEPRA_PRO_SR5900P_analysis](https://github.com/Mine02C4/TEPRA_PRO_SR5900P_analysis) の解析に基づいています。

## ライセンス

[MIT](LICENSE)
