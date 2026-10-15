# 🐉 Dragon PC Master Monitor

<div align="center">

![Dragon PC Master Monitor](/static/icon.png)

**最強のPC状態・温度・ゲーム中負荷監視デスクトップモニター**  
*The Ultimate Hardware & Thermal Telemetry Suite for Windows*

[![License: MIT](https://img.shields.io/badge/License-MIT-00f0ff.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-00ff9d.svg)](#)
[![Data Protection](https://img.shields.io/badge/Storage-Explorer%20Write%20Prohibited%20(RAM%20Only)-ff0055.svg)](#)
[![Release](https://img.shields.io/badge/Release-v1.0.0-b026ff.svg)](#)

</div>

---

## 🌟 概要 (Overview)

**Dragon PC Master Monitor** は、パソコンのハードウェア状態（CPU・GPU・メモリ・ストレージ・ネットワーク・OS・温度）をリアルタイムに極限まで可視化するインストール型デスクトップアプリケーションです。

### 🔒 特徴的な設計理念: エクスプローラー保存禁止 (RAM完全保持)
本アプリケーションは、ユーザーのファイルシステム（エクスプローラー）を一切汚さない厳格なセキュリティポリシーを採用しています。
- **ショートカットのみ追加**: インストール時はデスクトップとスタートメニューに起動用ショートカットのみを配置します。
- **データのエクスプローラー保存禁止**: ゲーム中の負荷ログやベンチマークデータはすべて揮発性RAM（メインメモリ）内でのみ処理・分析され、外部ストレージやエクスプローラーにファイル書き出しを行うことはありません。

---

## ⚡ 主な機能 (Key Features)

### 1. 🔥 高精度 CPU / GPU 温度監視 ＆ 高温警告システム
- **高精度サーマルゾーン監視**: 1/10℃単位の高精度センサーから温度をリアルタイム追跡。
- **多段階アラート判定**:
  - **NORMAL** (安定): 75℃未満
  - **CAUTION** (注意): 75℃ 〜 82℃
  - **WARNING** (警告): 82℃ 〜 88℃ (オレンジバナー表示)
  - **CRITICAL OVERHEAT** (極度危険): 88℃以上 (赤色ストロボ点滅 ＆ Web Audio API警告ビープ音自動発令)
- **警告音トグル**: ワンクリックで警告ビープ音のON/OFF切り替え可能。

### 2. 🎮 ゲーム中負荷記録（フライトレコーダー）
- **ワンクリック記録**: ゲームプレイ開始時に「記録開始 (START RECORD)」、終了時に「記録停止＆解析 (STOP & ANALYZE)」。
- **自動ボトルネック分析**:
  - CPU平均/最大負荷、GPU平均/最大負荷、最高到達温度、ピークメモリを即座に算出。
  - 「GPU律速」「CPU律速」「サーマルスロットリング警戒」「均衡」をAIライクに自動診断。
  - セッション全体のタイムライン推移チャートをグラフィカルに可視化。

### 3. 📊 リアルタイム総合ダッシュボード
- **CPU使用率・クロック周波数**: 全体使用率および現在MHz。
- **GPU 3D描画負荷率**: DirectX / Direct3D パイプラインを直接トラッキング。
- **メモリ (RAM)**: 使用中/全体GB、空き容量、使用率%。
- **リアルタイム波形チャート**: CPU負荷・温度、GPU負荷・メモリの直近30秒デュアルラインチャート。
- **ストレージ＆I/O**: 各ドライブの空き領域、リアルタイムRead/Write速度、ネット上り/下り速度。

### 4. 🖥️ パソコン詳細・全スペック表示
- **プロセッサ詳細**: モデル名、物理コア数、論理スレッド数、アーキテクチャ、全コア個別使用率バー。
- **グラフィックス詳細**: GPUモデル名、ドライバーバージョン、ビデオメモリ (VRAM)。
- **マザーボード＆BIOS**: メーカー、モデル番号、BIOSバージョン。
- **OS＆システム**: Windowsエディション、ビルド番号、システム稼働時間 (Uptime)、バッテリー充電状態。

### 5. ⚙️ 高負荷プロセス監視
- バックグラウンドで動作しているプロセスのCPU・メモリ消費量トップランキングをリアルタイム追跡。

---

## 🚀 インストール方法 (Installation)

1. [Releases](https://github.com/youyouboydragonOfficial/DragonPCMaster/releases) から最新の `DragonPCMaster-v1.0.0-Windows.zip` をダウンロードします。
2. ZIPを解凍し、中にある **`install.bat`** をダブルクリックして実行します。
3. デスクトップおよびスタートメニューに **『Dragon PC Master Monitor』** のショートカットが自動生成されます。
4. ショートカットをダブルクリックするだけで、コマンドプロンプト等の黒い画面なしで美しいアプリウィンドウが起動します！

---

## 🛠️ 開発・直接実行 (Development)

```powershell
# 依存パッケージのインストール
pip install psutil pywebview flask pillow

# アプリアイコンの生成 (初回のみ)
python generate_icon.py

# アプリの起動
python main.py
```

---

## 📜 ライセンス (License)

本プロジェクトは MIT License の下で公開されています。

---

<div align="center">

**© by youyouboydragon**

</div>
