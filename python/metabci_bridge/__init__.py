"""MetaBCI Bridge — MI classification for 跳一跳 game.

Offline: import raw EEG + trial timestamps → clean → slice → train.
Online:  LSL stream → clean → classify → WebSocket labels to game.
"""
