extends Node2D

const PLATFORM_SCENE: PackedScene = preload("res://scenes/Platform.tscn")
# Vertical Train Mode Constants (add after other consts)
const VERTICAL_TRAIN_PROMPT_TRIGGER_DELAY_NEW: float = 0.8
const VERTICAL_TRAIN_PROMPT_FLASH_DURATION: float = 0.6
const VERTICAL_TRAIN_PROMPT_TRIGGER_DELAY_RETURN: float = 0.5
const START_X: float = 140.0
const START_Y: float = 540.0
const START_WIDTH: float = 240.0
const START_PLATFORM_COUNT: int = 8
const BASE_SPAWN_DISTANCE_MIN: float = 180.0
const BASE_SPAWN_DISTANCE_MAX: float = 320.0
const HARD_SPAWN_DISTANCE_MIN: float = 245.0
const HARD_SPAWN_DISTANCE_MAX: float = 430.0
const BASE_PLATFORM_WIDTH_MIN: float = 120.0
const BASE_PLATFORM_WIDTH_MAX: float = 230.0
const HARD_PLATFORM_WIDTH_MIN: float = 86.0
const HARD_PLATFORM_WIDTH_MAX: float = 165.0
const PLATFORM_BUFFER_AHEAD: float = 1500.0
const PLATFORM_CLEANUP_BEHIND: float = 64.0
const CAMERA_LEAD_X: float = 557.6
const CAMERA_FIXED_Y: float = 340.0
const CAMERA_FOLLOW_SMOOTHNESS: float = 7.0
const CAMERA_MAX_SCROLL_SPEED: float = 880.0
const PLATFORM_MOTION_SCALE: float = 0.86
const LANDING_X_MARGIN: float = 3.0
const LANDING_Y_SNAP: float = 14.0
const MIN_LANDING_SUPPORT_WIDTH: float = 12.0
const MIN_STABLE_SUPPORT_WIDTH: float = 16.0
const AMBIGUOUS_SUPPORT_DIFF: float = 6.0
const MIN_DOMINANT_SUPPORT_WIDTH: float = 24.0
const LANDING_X_CLAMP_PADDING: float = 1.0
const PERFECT_RATIO_THRESHOLD: float = 0.09
const PERFECT_BASE_SCORE: int = 2
const NORMAL_BASE_SCORE: int = 1
const PERFECT_COMBO_MULTIPLIER: int = 2
const SPECIAL_BASE_CHANCE: float = 0.1
const SPECIAL_MAX_CHANCE: float = 0.52
const DIFFICULTY_SCORE_TARGET: float = 120.0
const FEEDBACK_SHOW_TIME: float = 0.9
const SFX_SAMPLE_RATE: float = 44100.0
const SFX_BUFFER_LENGTH: float = 0.2
const SETTINGS_FILE_PATH: String = "user://settings.json"
const RECORDS_FILE_PATH: String = "user://records.json"
const MAX_RECORDS: int = 10
const REALTIME_WS_URL: String = "ws://127.0.0.1:8765"
const REALTIME_SEND_INTERVAL: float = 0.05
const REALTIME_RECONNECT_INTERVAL: float = 1.0
const PERFECT_DISPLAY_EXTEND: float = 2.0
const PERFECT_IDLE_HIDE_DELAY: float = 1.0
const COMBO_INTERVAL_LIMIT: float = 1.0
const COMBO_DISPLAY_TIME: float = 1.0
const RACE_DURATION_DEFAULT: int = 60
const RACE_DURATION_OPTIONS: Array[int] = [30, 60, 90]
# Vertical Left-Right Mode Constants
const VERTICAL_LR_START_X: float = 800.0
const VERTICAL_LR_START_Y: float = 120.0
const VERTICAL_LR_END_Y: float = 2700.0
const VERTICAL_LR_JUMP_DISTANCE: float = 220.0
const VERTICAL_LR_JUMP_HORIZONTAL_SPEED: float = 270.0
const VERTICAL_LR_JUMP_HEIGHT: float = 600.0
const VERTICAL_LR_MISS_MARGIN: float = 36.0
const VERTICAL_LR_TRIAL_DURATION_DEFAULT: int = 120
const VERTICAL_LR_FINAL_PLATFORM_BUFFER: float = 58.0
const VERTICAL_LR_TREASURE_Y_OFFSET: float = 82.0
const VERTICAL_LR_TREASURE_BOX_WIDTH: float = 74.0
const VERTICAL_LR_TREASURE_BOX_HEIGHT: float = 52.0
const VERTICAL_LR_TREASURE_LID_HEIGHT: float = 18.0
const VERTICAL_TRAIN_START_X: float = 800.0
const VERTICAL_TRAIN_START_Y: float = 120.0
const VERTICAL_TRAIN_EDGE_DISTANCE: float = 90.0
const VERTICAL_TRAIN_LAYER_GAP: float = 220.0
const VERTICAL_TRAIN_PLATFORM_WIDTH: float = 170.0
const VERTICAL_TRAIN_TOTAL_LAYERS: int = 10
const VERTICAL_TRAIN_JUMP_DURATION: float = 1.0
const VERTICAL_TRAIN_CYCLE_DURATION: float = 10.0
const VERTICAL_TRAIN_START_FLASH_DURATION: float = 2.0
const VERTICAL_TRAIN_TASK_PHASE_END: float = 6.0
const VERTICAL_TRAIN_JUMP_PHASE_END: float = 7.0
const VERTICAL_TRAIN_SCORE_PHASE_END: float = 8.0
const VERTICAL_TRAIN_ARROW_FLASH_SPEED: float = 16.0
const VERTICAL_LR_LAYOUT_ROWS: Array = [
	{"y": 260.0, "platforms": [{"x": 520.0, "width": 162.0}, {"x": 800.0, "width": 176.0}]},
	{"y": 520.0, "platforms": [{"x": 1080.0, "width": 156.0}]},
	{"y": 780.0, "platforms": [{"x": 520.0, "width": 156.0}, {"x": 800.0, "width": 176.0}]},
	{"y": 1040.0, "platforms": [{"x": 1080.0, "width": 156.0}]},
	{"y": 1300.0, "platforms": [{"x": 520.0, "width": 162.0}, {"x": 800.0, "width": 180.0}]},
	{"y": 1560.0, "platforms": [{"x": 1080.0, "width": 156.0}]},
	{"y": 1820.0, "platforms": [{"x": 520.0, "width": 156.0}, {"x": 800.0, "width": 176.0}]},
	{"y": 2080.0, "platforms": [{"x": 1080.0, "width": 162.0}]},
	{"y": 2340.0, "platforms": [{"x": 520.0, "width": 162.0}, {"x": 800.0, "width": 176.0}]},
	{"y": 2600.0, "platforms": [{"x": 800.0, "width": 220.0, "treasure": true}, {"x": 1080.0, "width": 156.0}]}
]
const MI_OFFLINE_WS_URL: String = "ws://127.0.0.1:8766"
const MI_ONLINE_WS_URL: String = "ws://127.0.0.1:8767"
const MI_RECONNECT_INTERVAL: float = 0.75
const MI_PACKET_TTL_MS: int = 1500
const MI_HAND_CONF_THRESHOLD: float = 0.7
const MI_FOOT_CONF_THRESHOLD: float = 0.72
const MI_HAND_CONFIRM_COUNT: int = 3
const MI_FOOT_CONFIRM_COUNT: int = 2
const MI_KEEPALIVE_TIMEOUT: float = 0.7
const MI_ACTION_COOLDOWN: float = 0.12
const MI_AIR_JUMP_COOLDOWN: float = 0.2
const MI_STATUS_SEND_INTERVAL: float = 0.1
const MANUAL_MAX_CHARGE_TIME: float = 1.2
const MI_MAX_CHARGE_TIME: float = 2.5
const MI_HAND_ACTIVATION_DELAY: float = 0.5
const MI_SEQ_FIELD_CANDIDATES: Array[String] = ["seq", "sequence", "id"]
const MI_TIMESTAMP_FIELD_CANDIDATES: Array[String] = ["timestamp_ms", "ts_ms", "timestamp", "ts", "time"]
const MI_LABEL_FIELD_CANDIDATES: Array[String] = ["label", "mi_label", "command", "state"]
const MI_CONFIDENCE_FIELD_CANDIDATES: Array[String] = ["confidence", "conf", "prob", "score"]
const MI_CLASS_ID_FIELD_CANDIDATES: Array[String] = ["class_id", "label_id", "class"]
const MI_CLASS_ID_TO_LABEL_DEFAULT: Dictionary = {
	0: "rest",
	1: "hand",
	2: "foot"
}

enum GameState {
	START,
	PLAYING,
	GAME_OVER
}

enum GameMode {
	CLASSIC,
	RACE,
	VERTICAL_LR,
	VERTICAL_TRAIN,
	
}

enum ControlMode {
	MANUAL,
	MI
}

enum MIInputMode {
	OFFLINE,
	ONLINE
}

enum InputAction {
	NONE,
	START_CHARGE,
	CANCEL_CHARGE,
	RELEASE_JUMP,
	AIR_JUMP,
	MOVE_LEFT,
	MOVE_RIGHT,
	JUMP_LEFT,
	JUMP_RIGHT
}

enum MIState {
	IDLE,
	CHARGING,
	REST_KEEPALIVE,
	AIRBORNE,
	VERTICAL_LEFT_PENDING,
	VERTICAL_RIGHT_PENDING,
	VERTICAL_CHOOSING
}

@onready var player: Player = $Player
@onready var platforms_root: Node2D = $Platforms
@onready var camera_2d: Camera2D = $Camera2D
@onready var score_label: Label = $HUD/ScoreLabel
@onready var state_label: Label = $HUD/StateLabel
@onready var start_label: Label = $HUD/StartLabel
@onready var brightness_label: Label = $HUD/BrightnessLabel
@onready var volume_label: Label = $HUD/VolumeLabel
@onready var network_label: Label = $HUD/NetworkLabel
@onready var language_label: Label = $HUD/LanguageLabel
@onready var language_option: OptionButton = $HUD/LanguageOption
@onready var mode_label: Label = $HUD/ModeLabel
@onready var mode_option: OptionButton = $HUD/ModeOption
@onready var duration_label: Label = $HUD/DurationLabel
@onready var duration_option: OptionButton = $HUD/DurationOption
@onready var control_label: Label = $HUD/ControlLabel
@onready var control_option: OptionButton = $HUD/ControlOption
@onready var mi_input_label: Label = $HUD/MIInputLabel
@onready var mi_input_option: OptionButton = $HUD/MIInputOption
@onready var player_name_edit: LineEdit = $HUD/PlayerNameEdit
@onready var records_title: Label = $HUD/RecordsTitle
@onready var records_label: Label = $HUD/RecordsLabel
@onready var perfect_count_label: Label = $HUD/PerfectCountLabel
@onready var combo_label: Label = $HUD/ComboLabel
@onready var race_info_label: Label = $HUD/RaceInfoLabel
@onready var platform_minimap: Control = $HUD/PlatformMinimap

# Vertical Train Mode additional variables
var vertical_train_cycle_time: float = 0.0
var vertical_train_auto_jump_triggered: bool = false
var vertical_train_arrow_flash_timer: float = 0.0
var vertical_train_score_flash_timer: float = 0.0
var vertical_train_arrow_indicator_host: Platform = null
var vertical_train_arrow_indicator: Polygon2D = null   # 备用引用，如果不需要可保留 null
var rng: RandomNumberGenerator = RandomNumberGenerator.new()
var score: int = 0
var game_state: GameState = GameState.START
var wait_for_accept_release: bool = true
var next_platform_x: float = START_X
var brightness: float = 0.7
var sfx_volume: float = 0.65
var full_charge_cue_played: bool = false
var perfect_combo_streak: int = 0
var feedback_text: String = ""
var feedback_timer: float = 0.0
var standing_platform: Platform = null
var standing_platform_last_x: float = 0.0
var recent_records: Array = []
var perfect_count_in_run: int = 0
var perfect_display_timer: float = 0.0
var perfect_idle_timer: float = 0.0
var combo_count: int = 0
var combo_display_timer: float = 0.0
var last_jump_time_sec: float = -1.0
var realtime_ws: WebSocketPeer = WebSocketPeer.new()
var realtime_send_cooldown: float = 0.0
var realtime_reconnect_cooldown: float = 0.0
var realtime_difficulty_scale: float = -1.0
var current_language: String = "zh"
var current_mode: GameMode = GameMode.CLASSIC
var current_control_mode: ControlMode = ControlMode.MANUAL
var current_mi_input_mode: MIInputMode = MIInputMode.OFFLINE
var race_time_left: float = 0.0
var race_start_x: float = START_X
var race_distance: int = 0
var race_duration_seconds: int = RACE_DURATION_DEFAULT
var mi_offline_ws_url: String = MI_OFFLINE_WS_URL
var mi_online_ws_url: String = MI_ONLINE_WS_URL
var mi_class_id_to_label: Dictionary = MI_CLASS_ID_TO_LABEL_DEFAULT.duplicate(true)

var input_action_pending: InputAction = InputAction.NONE
var mi_state: MIState = MIState.IDLE
var mi_keepalive_timer: float = 0.0
var mi_air_jump_used: bool = false
var mi_last_action_time: float = -10.0
var mi_last_air_jump_time: float = -10.0
var mi_hand_activation_timer: float = 0.0

var mi_ws: WebSocketPeer = WebSocketPeer.new()
var mi_reconnect_cooldown: float = 0.0
var mi_last_seq: int = -1
var mi_raw_label: String = "none"
var mi_raw_streak: int = 0
var mi_decision_label: String = "none"

var mi_messages_received: int = 0
var mi_out_of_order_dropped: int = 0
var mi_stale_dropped: int = 0
var mi_invalid_action_count: int = 0
var mi_cancel_count: int = 0
var mi_air_jump_count: int = 0
var mi_action_count: int = 0
var mi_latency_ms_ema: float = 0.0
var mi_status_send_cooldown: float = 0.0

# Vertical Left-Right Mode Variables
var vertical_lr_time_left: float = 0.0
var vertical_lr_start_time: float = 0.0
var vertical_lr_completion_time: float = 0.0
var vertical_lr_trial_duration: int = VERTICAL_LR_TRIAL_DURATION_DEFAULT
var vertical_lr_difficulty_scale: float = 0.0
var vertical_lr_current_platform: Platform = null
var vertical_lr_left_option: Platform = null
var vertical_lr_right_option: Platform = null
var vertical_lr_expected_platform: Platform = null
var vertical_lr_row_platforms: Array = []
var vertical_lr_stage_index: int = 0
var vertical_lr_jump_locked: bool = false
var vertical_lr_finished: bool = false
var vertical_lr_success: bool = false
var vertical_lr_fail_pending: bool = false
var vertical_lr_fail_timer: float = 0.0
var vertical_lr_treasure_chest: Node2D = null
var vertical_lr_treasure_platform: Platform = null
var vertical_lr_treasure_collected: bool = false

var vertical_train_current_platform: Platform = null
var vertical_train_next_platform: Platform = null
var vertical_train_expected_platform: Platform = null
var vertical_train_jump_locked: bool = false
var vertical_train_fail_pending: bool = false
var vertical_train_fail_timer: float = 0.0
var vertical_train_row_index: int = 0
var vertical_train_start_time: float = 0.0
var vertical_train_completion_time: float = 0.0
var vertical_train_prompt_flash_timer: float = 0.0
var vertical_train_prompt_idle_timer: float = 0.0
var vertical_train_prompt_should_repeat: bool = false
var vertical_train_prompt_delay_timer: float = 0.0
var vertical_train_prompt_pending: bool = false

# focus mode removed: related variables cleaned up

var i18n: Dictionary = {
	"zh": {
		"score": "得分",
		"brightness": "亮度",
		"volume": "音量",
		"network": "网络",
		"net_online": "强实时在线",
		"net_connecting": "连接中...",
		"net_offline": "离线",
		"mode": "模式",
		"mode_classic": "经典",
		"mode_race": "竞速赛",
		"mode_vertical_lr": "竖向左右",
		"mode_vertical_train": "关卡模式",
		"mode_focus_fly": "天空飞行",
		"control": "控制",
		"control_manual": "手操",
		"control_mi": "MI",
		"mi_input": "MI输入",
		"mi_input_offline": "离线",
		"mi_input_online": "在线",
		"state_mi_idle": "MI待机",
		"state_mi_charging": "MI蓄力中",
		"state_mi_keepalive": "MI保活中",
		"state_mi_airborne": "MI空中",
		"mi_metrics": "MI 收:%d 丢序:%d 过期:%d 取消:%d 二跳:%d 延迟:%.0fms",
		"race_time": "竞速时长",
		"language": "语言",
		"lang_zh": "中文",
		"lang_en": "English",
		"player_name_placeholder": "玩家名",
		"records_title": "最近10次记录",
		"records_empty": "暂无记录",
		"start_title": "跳一跳\n按空格开始",
		"state_start": "按空格开始",
		"start_focus_title": "天空飞行\n按空格开始",
		"state_focus_start": "按空格开始飞行，Esc 主动结束",
		"state_focus_over": "飞行结束 - 按空格重开",
		"state_game_over": "游戏结束 - 按空格重开",
		"state_race_over": "竞速结束 - 按空格重开",
		"state_vertical_lr_clear": "通关！ - 按空格重开",
		"state_vertical_lr_fail": "失败 - 按空格重开",
		"state_vertical_lr_falling": "坠落中...",
		"vertical_lr_completion": "通关用时 %.1f 秒",
		"vertical_lr_elapsed": "当前用时 %.1f 秒",
		"vertical_lr_select": "选择方向",
		"vertical_train_select": "关卡进行中",
		"vertical_train_progress": "层数 %d/%d | 用时 %.1f 秒",
		"state_vertical_train_prompt": "开始标签已发送",
		"state_vertical_train_wait": "等待操作...",
		"state_vertical_train_returning": "返回原平台中...",
		"state_vertical_train_clear": "通关！ - 按空格重开",
		"state_vertical_train_over": "关卡完成 - 按空格重开",
		"layer": "层数",
		"vertical_lr_trial": "时间 %.1f | 步数 %d",
		"state_flying": "飞行中",
		"state_focus_flying": "飞行中，Esc 主动结束",
		"focus_info": "飞行 %.0f%% | 持续 %.1fs",
		"height": "高度",
		"state_charging": "蓄力 %.0f%%",
		"state_idle": "按住空格蓄力，松开起跳",
		"distance": "距离",
		"race_info": "倒计时 %.1fs | 距离 %d",
		"perfect_count": "完美次数: %d",
		"combo": "连击 x%d",
		"feedback_perfect": "完美 +%d",
		"feedback_perfect_combo": "完美连击 x2 +%d",
		"feedback_land": "落地 +%d",
		"feedback_risk": "（风险 +%d）",
		"record_line": "%02d. %s | %s | %s",
		"default_player": "玩家"
	},
	"en": {
		"score": "Score",
		"brightness": "Brightness",
		"volume": "Volume",
		"network": "Net",
		"net_online": "Realtime Online",
		"net_connecting": "Connecting...",
		"net_offline": "Offline",
		"mode": "Mode",
		"mode_classic": "Classic",
		"mode_race": "Race",
		"mode_vertical_lr": "Vertical LR",
		"mode_vertical_train": "Level Mode",
		"mode_focus_fly": "Sky Flight",
		"control": "Control",
		"control_manual": "Manual",
		"control_mi": "MI",
		"mi_input": "MI Input",
		"mi_input_offline": "Offline",
		"mi_input_online": "Online",
		"state_mi_idle": "MI Idle",
		"state_mi_charging": "MI Charging",
		"state_mi_keepalive": "MI Keepalive",
		"state_mi_airborne": "MI Airborne",
		"mi_metrics": "MI rx:%d oo:%d stale:%d cancel:%d air:%d lag:%.0fms",
		"race_time": "Race Time",
		"language": "Language",
		"lang_zh": "Chinese",
		"lang_en": "English",
		"player_name_placeholder": "Player name",
		"records_title": "Recent 10 Records",
		"records_empty": "No records yet.",
		"start_title": "JUMP JUMP\nPress Space to Start",
		"state_start": "Press Space to Start",
		"start_focus_title": "Sky Flight\nPress Space to Start",
		"state_focus_start": "Press Space to Start Flying, Esc to End",
		"state_focus_over": "Flight Over - Press Space to Restart",
		"state_game_over": "Game Over - Press Space to Restart",
		"state_race_over": "Race Over - Press Space to Restart",
		"state_vertical_lr_clear": "Clear! - Press Space to Restart",
		"state_vertical_lr_fail": "Failed - Press Space to Restart",
		"state_vertical_lr_falling": "Falling...",
		"vertical_lr_completion": "Clear Time: %.1f sec",
		"vertical_lr_elapsed": "Elapsed: %.1f sec",
		"vertical_lr_select": "Select Direction",
		"vertical_train_select": "Level Running",
		"vertical_train_progress": "Layers %d/%d | Time %.1f sec",
		"state_vertical_train_prompt": "Start label sent",
		"state_vertical_train_wait": "Waiting...",
		"state_vertical_train_returning": "Returning to platform...",
		"state_vertical_train_clear": "Clear! - Press Space to Restart",
		"state_vertical_train_over": "Level Complete - Press Space to Restart",
		"layer": "Layers",
		"vertical_lr_trial": "Time %.1f | Steps %d",
		"state_flying": "Flying",
		"state_focus_flying": "Flying, Esc to End",
		"focus_info": "Flight %.0f%% | Alive %.1fs",
		"height": "Height",
		"state_charging": "Charging %.0f%%",
		"state_idle": "Hold Space to Charge, Release to Jump",
		"distance": "Distance",
		"race_info": "Time %.1fs | Dist %d",
		"perfect_count": "Perfect Count: %d",
		"combo": "Combo x%d",
		"feedback_perfect": "Perfect +%d",
		"feedback_perfect_combo": "Perfect Combo x2 +%d",
		"feedback_land": "Land +%d",
		"feedback_risk": "(Risk +%d)",
		"record_line": "%02d. %s | %s | %s",
		"default_player": "Player"
	}
}

var sfx_land_player: AudioStreamPlayer
var sfx_perfect_player: AudioStreamPlayer
var sfx_fail_player: AudioStreamPlayer
var sfx_charge_player: AudioStreamPlayer
var sfx_train_cheer_player: AudioStreamPlayer

const BRIGHTNESS_MIN: float = 0.55
const BRIGHTNESS_MAX: float = 1.25
const BRIGHTNESS_STEP: float = 0.05
const SFX_VOLUME_MIN: float = 0.0
const SFX_VOLUME_MAX: float = 1.0
const SFX_VOLUME_STEP: float = 0.05

func _ready() -> void:
	rng.randomize()
	_setup_sfx_players()
	_load_settings()
	_setup_language_option()
	_setup_control_option()
	_setup_mode_option()
	_setup_duration_option()
	_setup_mi_input_option()
	_load_records()
	_apply_charge_profile()
	_apply_sfx_volume()
	_setup_run()
	game_state = GameState.START
	_apply_brightness()
	_refresh_ui()

func _setup_language_option() -> void:
	language_option.clear()
	language_option.add_item(_t("lang_zh"))
	language_option.set_item_metadata(0, "zh")
	language_option.add_item(_t("lang_en"))
	language_option.set_item_metadata(1, "en")
	var selected_idx: int = 0 if current_language == "zh" else 1
	language_option.select(selected_idx)
	_apply_option_popup_theme(language_option)
	if not language_option.item_selected.is_connected(_on_language_selected):
		language_option.item_selected.connect(_on_language_selected)

func _on_language_selected(index: int) -> void:
	var lang: Variant = language_option.get_item_metadata(index)
	if lang is String and (lang == "zh" or lang == "en"):
		current_language = lang
		_setup_language_option()
		_setup_control_option()
		_setup_mode_option()
		_setup_duration_option()
		_setup_mi_input_option()
		_save_settings()
		_update_records_display()
		_refresh_ui()

func _setup_control_option() -> void:
	control_option.clear()
	control_option.add_item(_t("control_manual"))
	control_option.set_item_metadata(0, ControlMode.MANUAL)
	control_option.add_item(_t("control_mi"))
	control_option.set_item_metadata(1, ControlMode.MI)
	control_option.select(0 if current_control_mode == ControlMode.MANUAL else 1)
	_apply_option_popup_theme(control_option)
	if not control_option.item_selected.is_connected(_on_control_selected):
		control_option.item_selected.connect(_on_control_selected)

func _on_control_selected(index: int) -> void:
	var selected: Variant = control_option.get_item_metadata(index)
	if selected is int:
		current_control_mode = selected
		_apply_charge_profile()
		_reset_mi_runtime_state()
		_save_settings()
		_refresh_ui()

func _setup_mode_option() -> void:
	mode_option.clear()
	mode_option.add_item(_t("mode_classic"))
	mode_option.set_item_metadata(0, GameMode.CLASSIC)
	mode_option.add_item(_t("mode_race"))
	mode_option.set_item_metadata(1, GameMode.RACE)
	mode_option.add_item(_t("mode_vertical_lr"))
	mode_option.set_item_metadata(2, GameMode.VERTICAL_LR)
	mode_option.add_item(_t("mode_vertical_train"))
	mode_option.set_item_metadata(3, GameMode.VERTICAL_TRAIN)
	var selected_idx: int = 0
	if current_mode == GameMode.CLASSIC:
		selected_idx = 0
	elif current_mode == GameMode.RACE:
		selected_idx = 1
	elif current_mode == GameMode.VERTICAL_LR:
		selected_idx = 2
	elif current_mode == GameMode.VERTICAL_TRAIN:
		selected_idx = 3
	mode_option.select(selected_idx)
	_apply_option_popup_theme(mode_option)
	if not mode_option.item_selected.is_connected(_on_mode_selected):
		mode_option.item_selected.connect(_on_mode_selected)

func _setup_duration_option() -> void:
	duration_option.clear()
	for value: int in RACE_DURATION_OPTIONS:
		duration_option.add_item("%d s" % value)
		duration_option.set_item_metadata(duration_option.item_count - 1, value)
	var selected_idx: int = 0
	for i: int in range(RACE_DURATION_OPTIONS.size()):
		if RACE_DURATION_OPTIONS[i] == race_duration_seconds:
			selected_idx = i
			break
	duration_option.select(selected_idx)
	_apply_option_popup_theme(duration_option)
	if not duration_option.item_selected.is_connected(_on_duration_selected):
		duration_option.item_selected.connect(_on_duration_selected)

func _setup_mi_input_option() -> void:
	mi_input_option.clear()
	mi_input_option.add_item(_t("mi_input_offline"))
	mi_input_option.set_item_metadata(0, MIInputMode.OFFLINE)
	mi_input_option.add_item(_t("mi_input_online"))
	mi_input_option.set_item_metadata(1, MIInputMode.ONLINE)
	mi_input_option.select(0 if current_mi_input_mode == MIInputMode.OFFLINE else 1)
	_apply_option_popup_theme(mi_input_option)
	if not mi_input_option.item_selected.is_connected(_on_mi_input_selected):
		mi_input_option.item_selected.connect(_on_mi_input_selected)

func _on_mi_input_selected(index: int) -> void:
	var selected: Variant = mi_input_option.get_item_metadata(index)
	if selected is int:
		current_mi_input_mode = selected
		_reset_mi_runtime_state()
		_save_settings()
		_refresh_ui()

func _apply_charge_profile() -> void:
	if player == null:
		return
	player.max_charge_time = MI_MAX_CHARGE_TIME if current_control_mode == ControlMode.MI else MANUAL_MAX_CHARGE_TIME

func _apply_option_popup_theme(option: OptionButton) -> void:
	if option == null:
		return
	var popup: PopupMenu = option.get_popup()
	if popup == null:
		return
	var panel_style: StyleBoxFlat = StyleBoxFlat.new()
	panel_style.bg_color = Color(0.934, 0.912, 0.835, 1)
	panel_style.border_width_left = 1
	panel_style.border_width_top = 1
	panel_style.border_width_right = 1
	panel_style.border_width_bottom = 1
	panel_style.border_color = Color(0.364706, 0.52549, 0.392157, 0.75)
	var hover_style: StyleBoxFlat = panel_style.duplicate()
	hover_style.bg_color = panel_style.bg_color
	popup.add_theme_stylebox_override("panel", panel_style)
	popup.add_theme_stylebox_override("hover", hover_style)
	popup.add_theme_color_override("font_color", Color(0.247059, 0.407843, 0.286275, 1))
	popup.add_theme_color_override("font_hover_color", Color(0.247059, 0.407843, 0.286275, 1))
	popup.add_theme_color_override("font_pressed_color", Color(0.247059, 0.407843, 0.286275, 1))
	popup.add_theme_color_override("font_accelerator_color", Color(0.247059, 0.407843, 0.286275, 0.82))
	popup.add_theme_color_override("font_disabled_color", Color(0.247059, 0.407843, 0.286275, 0.55))

func _on_mode_selected(index: int) -> void:
	var mode_value: Variant = mode_option.get_item_metadata(index)
	if mode_value is int:
		current_mode = mode_value
		_save_settings()
		_refresh_ui()

func _on_duration_selected(index: int) -> void:
	var duration_value: Variant = duration_option.get_item_metadata(index)
	if duration_value is int:
		race_duration_seconds = duration_value
		_save_settings()
		_refresh_ui()

func _t(key: String) -> String:
	var pack: Dictionary = i18n.get(current_language, i18n["en"])
	return str(pack.get(key, key))

func _input(event: InputEvent) -> void:
	if not (event is InputEventKey) or event.echo:
		return
	var key_event: InputEventKey = event as InputEventKey
	if key_event.keycode == KEY_SPACE or key_event.keycode == KEY_A or key_event.keycode == KEY_D or key_event.keycode == KEY_LEFT or key_event.keycode == KEY_RIGHT:
		print("key event:", key_event.keycode, " pressed=", key_event.pressed, " mode=", current_mode, " state=", game_state)

	# focus mode removed: no special ESC handling here

	if key_event.keycode == KEY_SPACE or key_event.physical_keycode == KEY_SPACE:
		if not key_event.pressed:
			if current_mode != GameMode.VERTICAL_LR and current_mode != GameMode.VERTICAL_TRAIN and current_control_mode == ControlMode.MANUAL and game_state == GameState.PLAYING:
				if player.release_jump():
					_register_jump_combo()
			return
		if game_state == GameState.START:
			_save_settings()
			_setup_run()
			game_state = GameState.PLAYING
			wait_for_accept_release = true
			return
		if game_state == GameState.GAME_OVER:
			_setup_run()
			game_state = GameState.PLAYING
			wait_for_accept_release = true
			full_charge_cue_played = false
			return
		if current_mode != GameMode.VERTICAL_LR and current_mode != GameMode.VERTICAL_TRAIN and current_control_mode == ControlMode.MANUAL:
			if event.pressed:
				player.begin_charge()
			return

	if current_mode == GameMode.VERTICAL_LR and current_control_mode == ControlMode.MANUAL and game_state == GameState.PLAYING:
		if event.pressed:
			if key_event.keycode == KEY_A or key_event.physical_keycode == KEY_A or key_event.keycode == KEY_LEFT:
				_queue_input_action(InputAction.JUMP_LEFT)
			elif key_event.keycode == KEY_D or key_event.physical_keycode == KEY_D or key_event.keycode == KEY_RIGHT:
				_queue_input_action(InputAction.JUMP_RIGHT)
			_consume_input_action()


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_MINUS or event.keycode == KEY_KP_SUBTRACT:
			_adjust_brightness(-BRIGHTNESS_STEP)
		elif event.keycode == KEY_EQUAL or event.keycode == KEY_PLUS or event.keycode == KEY_KP_ADD:
			_adjust_brightness(BRIGHTNESS_STEP)
		elif event.keycode == KEY_BRACKETLEFT:
			_adjust_sfx_volume(-SFX_VOLUME_STEP)
		elif event.keycode == KEY_BRACKETRIGHT:
			_adjust_sfx_volume(SFX_VOLUME_STEP)

func _queue_input_action(action: InputAction) -> void:
	if action == InputAction.NONE:
		return
	if action > input_action_pending:
		input_action_pending = action

func _poll_manual_action() -> void:
	if player.is_airborne:
		return
	if Input.is_action_pressed("ui_accept"):
		_queue_input_action(InputAction.START_CHARGE)
	if Input.is_action_just_released("ui_accept"):
		_queue_input_action(InputAction.RELEASE_JUMP)

func _poll_mi_action(delta: float) -> void:
	# Vertical LR/Training modes use different MI state machine
	if current_mode == GameMode.VERTICAL_LR or current_mode == GameMode.VERTICAL_TRAIN:
		if mi_decision_label == "left":
			_queue_input_action(InputAction.JUMP_LEFT)
			_mi_reset_decision_tracking()
		elif mi_decision_label == "right":
			_queue_input_action(InputAction.JUMP_RIGHT)
			_mi_reset_decision_tracking()
		return
	
	if player.is_airborne:
		mi_state = MIState.AIRBORNE
	else:
		if mi_state == MIState.AIRBORNE:
			mi_state = MIState.IDLE
			mi_air_jump_used = false

	if mi_state == MIState.CHARGING:
		if mi_decision_label == "foot" and not player.is_airborne:
			_queue_input_action(InputAction.RELEASE_JUMP)
			_mi_reset_decision_tracking()
		elif mi_decision_label == "rest":
			mi_state = MIState.REST_KEEPALIVE
			mi_keepalive_timer = 0.0
			player.pause_charge()
			_mi_reset_decision_tracking()
	elif mi_state == MIState.REST_KEEPALIVE:
		mi_keepalive_timer += delta
		if mi_decision_label == "hand":
			mi_state = MIState.CHARGING
			player.resume_charge()
			_mi_reset_decision_tracking()
		elif mi_keepalive_timer >= MI_KEEPALIVE_TIMEOUT:
			_queue_input_action(InputAction.CANCEL_CHARGE)
			mi_keepalive_timer = 0.0
			_mi_reset_decision_tracking()
	elif mi_state == MIState.IDLE:
		if mi_decision_label == "hand" and not player.is_airborne:
			mi_hand_activation_timer += delta
			if mi_hand_activation_timer >= MI_HAND_ACTIVATION_DELAY:
				_queue_input_action(InputAction.START_CHARGE)
				mi_state = MIState.CHARGING
				mi_hand_activation_timer = 0.0
				_mi_reset_decision_tracking()
		else:
			mi_hand_activation_timer = 0.0
	elif mi_state == MIState.AIRBORNE:
		var now_sec: float = Time.get_ticks_msec() / 1000.0
		if mi_decision_label == "foot":
			if not mi_air_jump_used and now_sec - mi_last_air_jump_time >= MI_AIR_JUMP_COOLDOWN:
				_queue_input_action(InputAction.AIR_JUMP)
				mi_air_jump_used = true
				mi_last_air_jump_time = now_sec
			else:
				mi_invalid_action_count += 1
			_mi_reset_decision_tracking()

func _consume_input_action() -> void:
	var action: InputAction = input_action_pending
	if action == InputAction.NONE:
		return
	input_action_pending = InputAction.NONE

	if current_mode == GameMode.VERTICAL_LR:
		if action == InputAction.JUMP_LEFT:
			_execute_vertical_lr_jump(-1)
		elif action == InputAction.JUMP_RIGHT:
			_execute_vertical_lr_jump(1)
		return

	if current_mode == GameMode.VERTICAL_TRAIN:
		return

	if (current_mode == GameMode.VERTICAL_LR or current_mode == GameMode.VERTICAL_TRAIN) and action == InputAction.START_CHARGE:
		return

	var now_sec: float = Time.get_ticks_msec() / 1000.0
	if current_control_mode == ControlMode.MI and action != InputAction.AIR_JUMP and now_sec - mi_last_action_time < MI_ACTION_COOLDOWN:
		return

	if action == InputAction.START_CHARGE:
		player.begin_charge()
		if current_control_mode == ControlMode.MI:
			player.always_show_charge_bar = false
			mi_state = MIState.CHARGING
	elif action == InputAction.CANCEL_CHARGE:
		player.cancel_charge()
		mi_cancel_count += 1
		if current_control_mode == ControlMode.MI:
			mi_state = MIState.IDLE
	elif action == InputAction.RELEASE_JUMP:
		if player.release_jump():
			if current_control_mode == ControlMode.MI:
				mi_state = MIState.AIRBORNE
				mi_air_jump_used = false
			else:
				_register_jump_combo()
		else:
			mi_invalid_action_count += 1
	elif action == InputAction.AIR_JUMP:
		if current_control_mode == ControlMode.MI and player.air_jump():
			mi_air_jump_count += 1
		else:
			mi_invalid_action_count += 1

	if current_control_mode == ControlMode.MI:
		mi_action_count += 1
		mi_last_action_time = now_sec

func _physics_process(delta: float) -> void:
	if wait_for_accept_release:
		if not Input.is_action_pressed("ui_accept"):
			wait_for_accept_release = false
		_refresh_ui()
		return

	if game_state == GameState.START:
		if Input.is_action_just_pressed("ui_accept"):
			_save_settings()
			_setup_run()
			game_state = GameState.PLAYING
			wait_for_accept_release = true
		_refresh_ui()
		return

	if game_state == GameState.GAME_OVER:
		if Input.is_action_just_pressed("ui_accept"):
			_setup_run()
			game_state = GameState.PLAYING
			wait_for_accept_release = true
			full_charge_cue_played = false
		_refresh_ui()
		return

	if current_mode == GameMode.RACE:
		race_time_left = max(0.0, race_time_left - delta)
		race_distance = max(race_distance, int(max(0.0, player.global_position.x - race_start_x)))
		score = race_distance
		if race_time_left <= 0.0:
			game_state = GameState.GAME_OVER
			wait_for_accept_release = true
			perfect_combo_streak = 0
			standing_platform = null
			standing_platform_last_x = 0.0
			_save_record(score)
			_save_settings()
			_update_records_display()
			_refresh_ui()
			return
	elif current_mode == GameMode.VERTICAL_LR:
		vertical_lr_time_left = max(0.0, vertical_lr_time_left - delta)
		# Time's up
		if vertical_lr_time_left <= 0.0:
			_fail_vertical_lr_run()
	elif current_mode == GameMode.VERTICAL_TRAIN:
		_update_vertical_train_level(delta)
	# focus mode removed

	if current_mode == GameMode.CLASSIC and feedback_timer > 0.0:
		feedback_timer = max(0.0, feedback_timer - delta)
		if feedback_timer <= 0.0:
			feedback_text = ""

	_update_realtime_bridge(delta)
	if current_control_mode == ControlMode.MI:
		_update_mi_bridge(delta)

	if current_mode == GameMode.CLASSIC and perfect_display_timer > 0.0:
		perfect_display_timer = max(0.0, perfect_display_timer - delta)
		perfect_idle_timer += delta
		if perfect_display_timer <= 0.0 or perfect_idle_timer >= PERFECT_IDLE_HIDE_DELAY:
			perfect_display_timer = 0.0
			perfect_count_label.visible = false

	if current_mode == GameMode.CLASSIC and combo_display_timer > 0.0:
		combo_display_timer = max(0.0, combo_display_timer - delta)
		if combo_display_timer <= 0.0:
			combo_label.visible = false
			combo_count = 0

	if current_mode != GameMode.VERTICAL_LR and not player.is_airborne:
		_ensure_ground_support()

	if current_mode == GameMode.VERTICAL_LR:
		if current_control_mode == ControlMode.MI:
			_poll_mi_action(delta)
			_consume_input_action()
	else:
		# Classic and Race modes
		if current_control_mode == ControlMode.MANUAL:
			if not player.is_airborne:
				if Input.is_action_pressed("ui_accept"):
					player.begin_charge()
				if Input.is_action_just_released("ui_accept"):
					if player.release_jump():
						_register_jump_combo()
		else:
			_poll_mi_action(delta)
			_consume_input_action()

	if player.is_charging and not full_charge_cue_played and player.charge_ratio() >= 0.995:
		_play_charge_ready_sfx()
		full_charge_cue_played = true
	elif not player.is_charging:
		full_charge_cue_played = false

	var previous_feet_y: float = player.feet_y()
	player.update_motion(delta)

	if player.is_airborne and player.feet_y() >= previous_feet_y - 1.0:
		_try_land_on_platform(previous_feet_y, player.feet_y())

	if current_mode == GameMode.VERTICAL_LR and player.is_airborne:
		if vertical_lr_expected_platform != null:
			if player.feet_y() > vertical_lr_expected_platform.top_y() + VERTICAL_LR_MISS_MARGIN:
				vertical_lr_expected_platform = null
		else:
			var viewport_size: Vector2 = get_viewport_rect().size
			var bottom_limit: float = camera_2d.global_position.y + viewport_size.y * 0.5 + 120.0
			if player.global_position.y > bottom_limit:
				_fail_vertical_lr_run()
	elif current_mode == GameMode.VERTICAL_TRAIN and player.is_airborne:
		if vertical_train_expected_platform != null:
			if player.feet_y() > vertical_train_expected_platform.top_y() + VERTICAL_LR_MISS_MARGIN:
				_fail_vertical_train_run()
		else:
			var fallback_limit_y: float = player.global_position.y + 99999.0
			if vertical_train_current_platform != null and is_instance_valid(vertical_train_current_platform):
				fallback_limit_y = vertical_train_current_platform.top_y() + (VERTICAL_TRAIN_LAYER_GAP * 1.7)
			if player.feet_y() > fallback_limit_y:
				_fail_vertical_train_run()

	if vertical_lr_fail_pending:
		vertical_lr_fail_timer = max(0.0, vertical_lr_fail_timer - delta)
		if vertical_lr_fail_timer <= 0.0:
			_finalize_vertical_lr_fail()

	_follow_camera(delta)
	_maintain_platforms()
	_check_game_over()
	_refresh_ui()

func _setup_run() -> void:
	for child: Node in platforms_root.get_children():
		child.free()

	score = 0
	player.gravity = 1700.0
	next_platform_x = START_X
	full_charge_cue_played = false
	perfect_combo_streak = 0
	feedback_text = ""
	feedback_timer = 0.0
	standing_platform = null
	standing_platform_last_x = 0.0
	perfect_count_in_run = 0
	perfect_display_timer = 0.0
	perfect_idle_timer = 0.0
	combo_count = 0
	combo_display_timer = 0.0
	last_jump_time_sec = -1.0
	perfect_count_label.visible = false
	combo_label.visible = false
	race_info_label.visible = false
	race_time_left = float(race_duration_seconds)
	race_distance = 0
	_reset_mi_runtime_state()

	if current_mode == GameMode.VERTICAL_LR:
		vertical_lr_time_left = float(vertical_lr_trial_duration)
		vertical_lr_start_time = Time.get_ticks_msec() / 1000.0
		vertical_lr_completion_time = 0.0
		vertical_lr_difficulty_scale = 0.0
		vertical_lr_finished = false
		vertical_lr_success = false
		vertical_lr_jump_locked = false
		vertical_lr_expected_platform = null
		vertical_lr_fail_pending = false
		vertical_lr_fail_timer = 0.0
		vertical_lr_stage_index = 0
		vertical_lr_row_platforms.clear()
		vertical_lr_treasure_collected = false
		vertical_lr_treasure_platform = null
		if vertical_lr_treasure_chest != null and is_instance_valid(vertical_lr_treasure_chest):
			vertical_lr_treasure_chest.queue_free()
		vertical_lr_treasure_chest = null
		if platform_minimap != null and platform_minimap.has_method("clear_layout"):
			platform_minimap.call("clear_layout")
		_clear_vertical_lr_options()
		vertical_lr_current_platform = _create_platform_vertical_lr(VERTICAL_LR_START_X, VERTICAL_LR_START_Y, 220.0, Platform.PlatformKind.NORMAL)
		player.reset_to_platform(vertical_lr_current_platform)
		player.always_show_charge_bar = false
		camera_2d.global_position = Vector2(vertical_lr_current_platform.global_position.x, CAMERA_FIXED_Y)
		_build_vertical_lr_layout()
		_activate_vertical_lr_stage(0)
		race_info_label.visible = false
	elif current_mode == GameMode.VERTICAL_TRAIN:
		vertical_train_jump_locked = false
		vertical_train_expected_platform = null
		vertical_train_fail_pending = false
		vertical_train_fail_timer = 0.0
		vertical_train_row_index = 0
		vertical_train_start_time = Time.get_ticks_msec() / 1000.0
		vertical_train_completion_time = 0.0
		vertical_train_prompt_flash_timer = 0.0
		vertical_train_prompt_idle_timer = 0.0
		vertical_train_prompt_should_repeat = false
		vertical_train_prompt_delay_timer = 0.0
		vertical_train_prompt_pending = false
		if vertical_train_next_platform != null and is_instance_valid(vertical_train_next_platform):
			vertical_train_next_platform.queue_free()
		vertical_train_next_platform = null
		vertical_train_current_platform = _create_platform_vertical_lr(VERTICAL_TRAIN_START_X, VERTICAL_TRAIN_START_Y, 220.0, Platform.PlatformKind.NORMAL)
		player.reset_to_platform(vertical_train_current_platform)
		player.always_show_charge_bar = false
		camera_2d.global_position = Vector2(vertical_train_current_platform.global_position.x, CAMERA_FIXED_Y)
		_spawn_vertical_train_next_platform()
		race_info_label.visible = true
		_schedule_vertical_train_prompt(VERTICAL_TRAIN_PROMPT_TRIGGER_DELAY_NEW)
	# focus mode removed: fallthrough to default run setup
	else:
		var first_platform: Platform = _create_platform(START_X, START_Y, START_WIDTH, Platform.PlatformKind.NORMAL, 0.0)
		player.reset_to_platform(first_platform)
		player.always_show_charge_bar = current_control_mode == ControlMode.MANUAL
		standing_platform = first_platform
		standing_platform_last_x = first_platform.global_position.x
		race_start_x = player.global_position.x

		camera_2d.global_position = Vector2(player.global_position.x + CAMERA_LEAD_X, CAMERA_FIXED_Y)

		for _i: int in range(START_PLATFORM_COUNT):
			_spawn_next_platform(false)

	_refresh_ui()

func _create_platform(x: float, y: float, width: float, kind: Platform.PlatformKind, difficulty: float) -> Platform:
	var platform: Platform = PLATFORM_SCENE.instantiate()
	platform.global_position = Vector2(x, y)
	platforms_root.add_child(platform)
	platform.setup(kind, width, difficulty, rng, PLATFORM_MOTION_SCALE)
	return platform

func _spawn_next_platform(allow_special: bool = true) -> void:
	var difficulty: float = _difficulty_ratio()
	var min_distance: float = lerp(BASE_SPAWN_DISTANCE_MIN, HARD_SPAWN_DISTANCE_MIN, difficulty)
	var max_distance: float = lerp(BASE_SPAWN_DISTANCE_MAX, HARD_SPAWN_DISTANCE_MAX, difficulty)
	next_platform_x += rng.randf_range(min_distance, max_distance)
	var y: float = START_Y
	var min_width: float = lerp(BASE_PLATFORM_WIDTH_MIN, HARD_PLATFORM_WIDTH_MIN, difficulty)
	var max_width: float = lerp(BASE_PLATFORM_WIDTH_MAX, HARD_PLATFORM_WIDTH_MAX, difficulty)
	var kind: Platform.PlatformKind = _roll_platform_kind(difficulty, allow_special)
	var width: float = rng.randf_range(min_width, max_width)

	if kind == Platform.PlatformKind.FRAGILE:
		width *= 0.86

	width = clamp(width, 64.0, 260.0)
	_create_platform(next_platform_x, y, width, kind, difficulty)

func _create_platform_vertical_lr(x: float, y: float, width: float, kind: Platform.PlatformKind) -> Platform:
	var platform: Platform = PLATFORM_SCENE.instantiate()
	platform.global_position = Vector2(x, y)
	platforms_root.add_child(platform)
	platform.setup(kind, width, 0.0, rng, 0.0)
	return platform

func _spawn_next_platform_vertical_lr() -> void:
	_activate_vertical_lr_stage(vertical_lr_stage_index)

func _build_vertical_lr_layout() -> void:
	if not vertical_lr_row_platforms.is_empty():
		return
	for row_spec: Dictionary in VERTICAL_LR_LAYOUT_ROWS:
		var row_platforms: Array = []
		var row_y: float = float(row_spec.get("y", VERTICAL_LR_START_Y))
		var platform_specs: Array = row_spec.get("platforms", [])
		for platform_spec_variant: Variant in platform_specs:
			if not (platform_spec_variant is Dictionary):
				continue
			var platform_spec: Dictionary = platform_spec_variant
			var platform_x: float = float(platform_spec.get("x", VERTICAL_LR_START_X))
			var platform_width: float = float(platform_spec.get("width", 160.0))
			var platform_kind: Platform.PlatformKind = Platform.PlatformKind.NORMAL
			var platform: Platform = _create_platform_vertical_lr(platform_x, row_y, platform_width, platform_kind)
			row_platforms.append(platform)
			if bool(platform_spec.get("treasure", false)):
				vertical_lr_treasure_platform = platform
				_spawn_vertical_lr_treasure_chest(platform)
		vertical_lr_row_platforms.append(row_platforms)
	if platform_minimap != null and platform_minimap.has_method("set_layout"):
		platform_minimap.call("set_layout", VERTICAL_LR_LAYOUT_ROWS)

func _activate_vertical_lr_stage(stage_index: int) -> void:
	if stage_index < 0 or stage_index >= vertical_lr_row_platforms.size():
		vertical_lr_left_option = null
		vertical_lr_right_option = null
		if platform_minimap != null and platform_minimap.has_method("set_stage"):
			platform_minimap.call("set_stage", -1)
		return
	var row_platforms: Array = vertical_lr_row_platforms[stage_index]
	vertical_lr_left_option = null
	vertical_lr_right_option = null
	if platform_minimap != null and platform_minimap.has_method("set_stage"):
		platform_minimap.call("set_stage", stage_index)
	if row_platforms.is_empty():
		return

	var current_x: float = vertical_lr_current_platform.global_position.x if vertical_lr_current_platform != null and is_instance_valid(vertical_lr_current_platform) else VERTICAL_LR_START_X
	var best_left_delta: float = INF
	var best_right_delta: float = INF

	for platform_variant: Variant in row_platforms:
		var candidate: Platform = platform_variant as Platform
		if candidate == null or not is_instance_valid(candidate):
			continue
		var delta_x: float = candidate.global_position.x - current_x
		if delta_x < -8.0:
			var left_distance: float = abs(delta_x)
			if left_distance < best_left_delta:
				best_left_delta = left_distance
				vertical_lr_left_option = candidate
		elif delta_x > 8.0:
			var right_distance: float = abs(delta_x)
			if right_distance < best_right_delta:
				best_right_delta = right_distance
				vertical_lr_right_option = candidate

func _clear_vertical_lr_options() -> void:
	vertical_lr_left_option = null
	vertical_lr_right_option = null

func _spawn_vertical_lr_treasure_chest(platform: Platform) -> void:
	if vertical_lr_treasure_chest != null and is_instance_valid(vertical_lr_treasure_chest):
		vertical_lr_treasure_chest.queue_free()
		vertical_lr_treasure_chest = null

	var chest: Node2D = Node2D.new()
	chest.name = "TreasureChest"
	chest.z_index = 10
	platform.add_child(chest)
	chest.position = Vector2(0.0, -platform.height * 0.5 - VERTICAL_LR_TREASURE_Y_OFFSET)

	var glow: Polygon2D = Polygon2D.new()
	glow.color = Color(1.0, 0.88, 0.38, 0.18)
	glow.polygon = PackedVector2Array([
		Vector2(-60.0, -22.0),
		Vector2(60.0, -22.0),
		Vector2(76.0, 0.0),
		Vector2(60.0, 22.0),
		Vector2(-60.0, 22.0),
		Vector2(-76.0, 0.0)
	])
	chest.add_child(glow)

	var base: Polygon2D = Polygon2D.new()
	base.color = Color(0.49, 0.24, 0.08, 1.0)
	base.polygon = PackedVector2Array([
		Vector2(-VERTICAL_LR_TREASURE_BOX_WIDTH * 0.5, 0.0),
		Vector2(VERTICAL_LR_TREASURE_BOX_WIDTH * 0.5, 0.0),
		Vector2(VERTICAL_LR_TREASURE_BOX_WIDTH * 0.48, VERTICAL_LR_TREASURE_BOX_HEIGHT),
		Vector2(-VERTICAL_LR_TREASURE_BOX_WIDTH * 0.48, VERTICAL_LR_TREASURE_BOX_HEIGHT)
	])
	chest.add_child(base)

	var lid: Polygon2D = Polygon2D.new()
	lid.color = Color(0.80, 0.54, 0.18, 1.0)
	lid.polygon = PackedVector2Array([
		Vector2(-VERTICAL_LR_TREASURE_BOX_WIDTH * 0.54, -VERTICAL_LR_TREASURE_LID_HEIGHT),
		Vector2(VERTICAL_LR_TREASURE_BOX_WIDTH * 0.54, -VERTICAL_LR_TREASURE_LID_HEIGHT),
		Vector2(VERTICAL_LR_TREASURE_BOX_WIDTH * 0.42, 4.0),
		Vector2(-VERTICAL_LR_TREASURE_BOX_WIDTH * 0.42, 4.0)
	])
	chest.add_child(lid)

	var band: Polygon2D = Polygon2D.new()
	band.color = Color(0.97, 0.84, 0.32, 1.0)
	band.polygon = PackedVector2Array([
		Vector2(-8.0, -VERTICAL_LR_TREASURE_LID_HEIGHT),
		Vector2(8.0, -VERTICAL_LR_TREASURE_LID_HEIGHT),
		Vector2(8.0, VERTICAL_LR_TREASURE_BOX_HEIGHT),
		Vector2(-8.0, VERTICAL_LR_TREASURE_BOX_HEIGHT)
	])
	chest.add_child(band)

	var lock: Polygon2D = Polygon2D.new()
	lock.color = Color(0.98, 0.94, 0.58, 1.0)
	lock.polygon = PackedVector2Array([
		Vector2(-6.0, 8.0),
		Vector2(6.0, 8.0),
		Vector2(6.0, 24.0),
		Vector2(-6.0, 24.0)
	])
	chest.add_child(lock)

	var sparkle: Polygon2D = Polygon2D.new()
	sparkle.color = Color(1.0, 0.98, 0.70, 0.9)
	sparkle.polygon = PackedVector2Array([
		Vector2(0.0, -30.0),
		Vector2(6.0, -14.0),
		Vector2(22.0, -8.0),
		Vector2(6.0, -2.0),
		Vector2(0.0, 14.0),
		Vector2(-6.0, -2.0),
		Vector2(-22.0, -8.0),
		Vector2(-6.0, -14.0)
	])
	chest.add_child(sparkle)

	vertical_lr_treasure_chest = chest

func _execute_vertical_lr_jump(direction: int) -> void:
	if vertical_lr_finished or vertical_lr_jump_locked or player.is_airborne:
		return
	if direction == 0:
		return

	var target_platform: Platform = vertical_lr_left_option if direction < 0 else vertical_lr_right_option

	if not player.prepare_fixed_jump(float(direction), VERTICAL_LR_JUMP_HORIZONTAL_SPEED, VERTICAL_LR_JUMP_HEIGHT):
		return

	vertical_lr_expected_platform = target_platform if target_platform != null and is_instance_valid(target_platform) else null
	vertical_lr_jump_locked = true
	
func _maintain_platforms() -> void:
	if current_mode == GameMode.VERTICAL_LR or current_mode == GameMode.VERTICAL_TRAIN:
		return
	else:
		var target_x: float = player.global_position.x + PLATFORM_BUFFER_AHEAD
		while next_platform_x < target_x:
			_spawn_next_platform()

		var viewport_half_width: float = get_viewport_rect().size.x * 0.5
		var visible_left_x: float = camera_2d.global_position.x - viewport_half_width

		for child: Node in platforms_root.get_children():
			var platform: Platform = child as Platform
			if platform != null and platform.right_edge() < visible_left_x - PLATFORM_CLEANUP_BEHIND:
				platform.queue_free()

func _try_land_on_platform(previous_feet_y: float, current_feet_y: float) -> void:
	# Special handling for Vertical LR mode
	if current_mode == GameMode.VERTICAL_LR:
		_try_land_on_platform_vertical_lr(previous_feet_y, current_feet_y)
		return
	if current_mode == GameMode.VERTICAL_TRAIN:
		_try_land_on_platform_vertical_train(previous_feet_y, current_feet_y)
		return
	
	var best_platform: Platform = null
	var best_overlap: float = -1.0
	var second_overlap: float = -1.0
	var best_top_y: float = 0.0
	var best_vertical_delta: float = INF

	for child: Node in platforms_root.get_children():
		var platform: Platform = child as Platform
		if platform == null:
			continue
		if not platform.can_support_landing():
			continue
		var top_y: float = platform.top_y()
		var within_vertical: bool = previous_feet_y <= top_y + LANDING_Y_SNAP and current_feet_y >= top_y - LANDING_Y_SNAP
		if not within_vertical:
			continue

		var overlap_width: float = platform.support_overlap_width(player.global_position.x, Player.HALF_SIZE, LANDING_X_MARGIN)
		if overlap_width < MIN_LANDING_SUPPORT_WIDTH:
			continue

		var vertical_delta: float = abs(current_feet_y - top_y)
		if overlap_width > best_overlap or (is_equal_approx(overlap_width, best_overlap) and vertical_delta < best_vertical_delta):
			second_overlap = best_overlap
			best_overlap = overlap_width
			best_platform = platform
			best_top_y = top_y
			best_vertical_delta = vertical_delta
		elif overlap_width > second_overlap:
			second_overlap = overlap_width

	if best_platform == null:
		return

	# Crossing two neighboring platforms can create ambiguous support. Ignore landing unless one platform clearly dominates.
	if second_overlap >= 0.0 and abs(best_overlap - second_overlap) <= AMBIGUOUS_SUPPORT_DIFF and best_overlap < MIN_DOMINANT_SUPPORT_WIDTH:
		return

	if best_overlap < MIN_STABLE_SUPPORT_WIDTH:
		return

	var landing_offset: float = abs(player.global_position.x - best_platform.global_position.x)
	var perfect_threshold: float = max(10.0, best_platform.width * PERFECT_RATIO_THRESHOLD)
	var is_perfect: bool = landing_offset <= perfect_threshold
	var should_score: bool = player.can_score_landing()
	player.land_on(best_top_y)
	var clamp_min_x: float = best_platform.left_edge() + Player.HALF_SIZE + LANDING_X_CLAMP_PADDING
	var clamp_max_x: float = best_platform.right_edge() - Player.HALF_SIZE - LANDING_X_CLAMP_PADDING
	if clamp_min_x <= clamp_max_x:
		player.global_position.x = clamp(player.global_position.x, clamp_min_x, clamp_max_x)
	standing_platform = best_platform
	standing_platform_last_x = best_platform.global_position.x

	if not should_score:
		perfect_combo_streak = 0
		return

	if current_mode == GameMode.RACE:
		best_platform.on_landed()
		return

	var landing_score: int = NORMAL_BASE_SCORE
	if is_perfect:
		_register_perfect_count()
		perfect_combo_streak += 1
		landing_score = PERFECT_BASE_SCORE
		if perfect_combo_streak >= 2:
			landing_score *= PERFECT_COMBO_MULTIPLIER
	else:
		perfect_combo_streak = 0

	var bonus: int = best_platform.risk_bonus()
	landing_score += bonus
	score += landing_score
	best_platform.on_landed()
	_show_landing_feedback(is_perfect, bonus, landing_score)
	if is_perfect:
		_play_perfect_land_sfx()
	else:
		_play_land_sfx()

func _try_land_on_platform_vertical_lr(previous_feet_y: float, current_feet_y: float) -> void:
	var candidates: Array[Platform] = []
	for child: Node in platforms_root.get_children():
		var p: Platform = child as Platform
		if p == null:
			continue
		if not p.can_support_landing():
			continue
		candidates.append(p)

	if candidates.is_empty():
		return

	var platform: Platform = null
	var best_overlap: float = -1.0
	var best_vertical_delta: float = INF
	for candidate: Platform in candidates:
		var top_y_candidate: float = candidate.top_y()
		var within_vertical: bool = previous_feet_y <= top_y_candidate + LANDING_Y_SNAP and current_feet_y >= top_y_candidate - LANDING_Y_SNAP
		if not within_vertical:
			continue
		var overlap_width: float = candidate.support_overlap_width(player.global_position.x, Player.HALF_SIZE, LANDING_X_MARGIN)
		if overlap_width < MIN_STABLE_SUPPORT_WIDTH:
			continue
		var vertical_delta: float = abs(current_feet_y - top_y_candidate)
		if overlap_width > best_overlap or (is_equal_approx(overlap_width, best_overlap) and vertical_delta < best_vertical_delta):
			platform = candidate
			best_overlap = overlap_width
			best_vertical_delta = vertical_delta

	if platform == null:
		return

	var top_y: float = platform.top_y()

	player.land_on(top_y)
	var clamp_min_x: float = platform.left_edge() + Player.HALF_SIZE + LANDING_X_CLAMP_PADDING
	var clamp_max_x: float = platform.right_edge() - Player.HALF_SIZE - LANDING_X_CLAMP_PADDING
	if clamp_min_x <= clamp_max_x:
		player.global_position.x = clamp(player.global_position.x, clamp_min_x, clamp_max_x)
	standing_platform = platform
	standing_platform_last_x = platform.global_position.x
	vertical_lr_current_platform = platform
	vertical_lr_expected_platform = null
	vertical_lr_jump_locked = false
	score += 1
	if platform == vertical_lr_treasure_platform and not vertical_lr_treasure_collected:
		vertical_lr_treasure_collected = true
		score += 5
		if vertical_lr_treasure_chest != null and is_instance_valid(vertical_lr_treasure_chest):
			vertical_lr_treasure_chest.modulate = Color(1.0, 1.0, 1.0, 0.45)
	_play_land_sfx()

	var landed_row_index: int = _find_vertical_lr_row_index_for_platform(platform)
	_emit_vertical_lr_platform_label(platform, landed_row_index)
	if landed_row_index >= VERTICAL_LR_LAYOUT_ROWS.size() - 1:
		_complete_vertical_lr_run()
		return

	if landed_row_index >= 0:
		vertical_lr_stage_index = landed_row_index + 1
	else:
		vertical_lr_stage_index += 1
	_activate_vertical_lr_stage(vertical_lr_stage_index)
	if platform_minimap != null and platform_minimap.has_method("set_stage"):
		platform_minimap.call("set_stage", vertical_lr_stage_index)

func _find_vertical_lr_row_index_for_platform(platform: Platform) -> int:
	for row_index: int in range(vertical_lr_row_platforms.size()):
		var row_platforms: Array = vertical_lr_row_platforms[row_index]
		for candidate_variant: Variant in row_platforms:
			var candidate: Platform = candidate_variant as Platform
			if candidate == platform:
				return row_index
	return -1

func _emit_vertical_lr_platform_label(platform: Platform, row_index: int) -> void:
	if mi_ws == null or mi_ws.get_ready_state() != WebSocketPeer.STATE_OPEN:
		return
	var column_label: String = "center"
	if platform.global_position.x < VERTICAL_LR_START_X - 120.0:
		column_label = "left"
	elif platform.global_position.x > VERTICAL_LR_START_X + 120.0:
		column_label = "right"
	var payload: Dictionary = {
		"type": "trial_label",
		"timestamp_ms": int(Time.get_unix_time_from_system() * 1000.0),
		"mode": "vertical_lr",
		"row": row_index,
		"column": column_label,
		"label": column_label,
		"score": score,
		"same_layer": (row_index + 1 == vertical_lr_stage_index)
	}
	mi_ws.send_text(JSON.stringify(payload))

func _spawn_vertical_train_next_platform() -> void:
	if vertical_train_current_platform == null or not is_instance_valid(vertical_train_current_platform):
		return
	if vertical_train_next_platform != null and is_instance_valid(vertical_train_next_platform) and vertical_train_next_platform != vertical_train_current_platform:
		_vertical_train_clear_arrow_indicator()
		vertical_train_next_platform.queue_free()
		vertical_train_next_platform = null
	var next_y: float = vertical_train_current_platform.global_position.y + VERTICAL_TRAIN_LAYER_GAP
	var side: int = -1 if rng.randf() < 0.5 else 1
	var next_width: float = VERTICAL_TRAIN_PLATFORM_WIDTH
	var next_x: float = 0.0
	if side < 0:
		next_x = vertical_train_current_platform.left_edge() - VERTICAL_TRAIN_EDGE_DISTANCE - next_width * 0.5
	else:
		next_x = vertical_train_current_platform.right_edge() + VERTICAL_TRAIN_EDGE_DISTANCE + next_width * 0.5
	vertical_train_next_platform = _create_platform_vertical_lr(next_x, next_y, next_width, Platform.PlatformKind.NORMAL)
	vertical_train_expected_platform = vertical_train_next_platform
	_vertical_train_refresh_arrow_indicator()

func _vertical_train_mark_interaction() -> void:
	vertical_train_prompt_idle_timer = 0.0
	vertical_train_prompt_should_repeat = true

func _vertical_train_clear_arrow_indicator() -> void:
	if vertical_train_arrow_indicator_host != null and is_instance_valid(vertical_train_arrow_indicator_host):
		var host_marker: Polygon2D = vertical_train_arrow_indicator_host.marker
		if host_marker != null:
			host_marker.visible = false
			host_marker.modulate = Color(1.0, 1.0, 1.0, 1.0)
			# Restore the normal hidden marker state for a standard platform.
			vertical_train_arrow_indicator_host.marker.visible = false
	vertical_train_arrow_indicator_host = null
	vertical_train_arrow_indicator = null

func _vertical_train_refresh_arrow_indicator() -> void:
	_vertical_train_clear_arrow_indicator()
	if vertical_train_next_platform == null or not is_instance_valid(vertical_train_next_platform):
		return
	var host: Platform = vertical_train_next_platform
	var marker: Polygon2D = host.marker
	if marker == null:
		return
	vertical_train_arrow_indicator_host = host
	vertical_train_arrow_indicator = null
	marker.visible = true
	marker.modulate = Color(1.0, 1.0, 1.0, 0.95)
	marker.color = Color(1.0, 0.92, 0.36, 0.96)
	marker.position = Vector2(0.0, -host.height * 0.95)
	var arrow_w: float = min(42.0, host.width * 0.30)
	var arrow_h: float = min(18.0, host.height * 0.65)
	marker.scale = Vector2(1.0, 1.0 if vertical_train_current_platform == null else 1.0)
	var points_right: PackedVector2Array = PackedVector2Array([
		Vector2(-arrow_w * 0.60, -arrow_h * 0.35),
		Vector2(arrow_w * 0.02, -arrow_h * 0.35),
		Vector2(arrow_w * 0.02, -arrow_h * 0.75),
		Vector2(arrow_w * 0.62, 0.0),
		Vector2(arrow_w * 0.02, arrow_h * 0.75),
		Vector2(arrow_w * 0.02, arrow_h * 0.35),
		Vector2(-arrow_w * 0.60, arrow_h * 0.35)
	])
	marker.polygon = points_right
	if vertical_train_current_platform != null and is_instance_valid(vertical_train_current_platform):
		if host.global_position.x < vertical_train_current_platform.global_position.x:
			marker.scale = Vector2(-1.0, 1.0)
		else:
			marker.scale = Vector2(1.0, 1.0)

func _vertical_train_update_arrow_flash(delta: float) -> void:
	if vertical_train_arrow_indicator_host == null or not is_instance_valid(vertical_train_arrow_indicator_host):
		return
	var marker: Polygon2D = vertical_train_arrow_indicator_host.marker
	if marker == null or not marker.visible:
		return
	var pulse: float = 0.5 + 0.5 * sin(Time.get_ticks_msec() * 0.016 * VERTICAL_TRAIN_ARROW_FLASH_SPEED)
	marker.modulate = Color(1.0, 1.0, 1.0, 0.35 + 0.65 * pulse)

func _vertical_train_update_start_visuals(delta: float) -> void:
	_update_vertical_train_prompt_visuals(delta)

func _vertical_train_update_jump_visuals(delta: float) -> void:
	if player == null:
		return
	player.modulate = Color(brightness, brightness, brightness, 1.0)

func _vertical_train_update_score_phase(delta: float) -> void:
	if vertical_train_score_flash_timer <= 0.0:
		return  # 计时器已归零，无需继续
	vertical_train_score_flash_timer = max(0.0, vertical_train_score_flash_timer - delta)
	if player != null:
		var highlight: float = 0.65 + 0.35 * sin(Time.get_ticks_msec() * 0.015)
		player.modulate = Color(1.0, 0.98, 0.76, 1.0).lerp(Color(brightness, brightness, brightness, 1.0), 1.0 - highlight)

func _vertical_train_update_rest_visuals(delta: float) -> void:
	if player != null:
		player.modulate = Color(brightness, brightness, brightness, 1.0)
	if vertical_train_arrow_indicator_host != null and is_instance_valid(vertical_train_arrow_indicator_host):
		var marker: Polygon2D = vertical_train_arrow_indicator_host.marker
		if marker != null:
			marker.modulate = Color(1.0, 1.0, 1.0, 0.18)

func _play_vertical_train_cheer_sfx() -> void:
	_play_pattern(sfx_train_cheer_player, [Vector2(520.0, 0.06), Vector2(650.0, 0.06), Vector2(780.0, 0.08), Vector2(980.0, 0.10)], 0.26)

func _vertical_train_trigger_auto_jump() -> void:
	if vertical_train_current_platform == null or not is_instance_valid(vertical_train_current_platform):
		return
	if vertical_train_next_platform == null or not is_instance_valid(vertical_train_next_platform):
		return
	var delta_x: float = vertical_train_next_platform.global_position.x - vertical_train_current_platform.global_position.x
	var direction: float = -1.0 if delta_x < 0.0 else 1.0
	var jump_horizontal_speed: float = abs(delta_x) / VERTICAL_TRAIN_JUMP_DURATION
	var jump_vertical_speed: float = max(120.0, (player.gravity * 0.5) - VERTICAL_TRAIN_LAYER_GAP)
	vertical_train_auto_jump_triggered = true
	vertical_train_jump_locked = true
	vertical_train_expected_platform = vertical_train_next_platform
	player.launch_fixed_jump(direction, jump_horizontal_speed, jump_vertical_speed)

func _vertical_train_restart_cycle() -> void:
	vertical_train_cycle_time = 0.0
	vertical_train_prompt_flash_timer = VERTICAL_TRAIN_START_FLASH_DURATION
	vertical_train_prompt_idle_timer = 0.0
	vertical_train_prompt_should_repeat = true
	vertical_train_prompt_delay_timer = 0.0
	vertical_train_prompt_pending = false
	vertical_train_arrow_flash_timer = 0.0
	vertical_train_score_flash_timer = 0.0
	vertical_train_auto_jump_triggered = false
	_vertical_train_clear_arrow_indicator()
	_emit_vertical_train_start_label()

func _emit_vertical_train_start_label() -> void:
	if mi_ws == null or mi_ws.get_ready_state() != WebSocketPeer.STATE_OPEN:
		return
	var payload: Dictionary = {
		"type": "trial_label",
		"timestamp_ms": int(Time.get_unix_time_from_system() * 1000.0),
		"mode": "vertical_train",
		"layer": vertical_train_row_index,
		"target_layers": VERTICAL_TRAIN_TOTAL_LAYERS,
		"label": "start",
		"score": score
	}
	mi_ws.send_text(JSON.stringify(payload))

func _start_vertical_train_prompt() -> void:
	vertical_train_prompt_flash_timer = VERTICAL_TRAIN_PROMPT_FLASH_DURATION
	vertical_train_prompt_idle_timer = 0.0
	vertical_train_prompt_should_repeat = true
	_emit_vertical_train_start_label()

func _schedule_vertical_train_prompt(delay: float) -> void:
	vertical_train_prompt_pending = true
	vertical_train_prompt_delay_timer = delay
	vertical_train_prompt_idle_timer = 0.0
	vertical_train_prompt_should_repeat = true

func _update_vertical_train_prompt_visuals(delta: float) -> void:
	if player == null:
		return
	var base_tint: Color = Color(brightness, brightness, brightness, 1.0)
	if vertical_train_prompt_flash_timer > 0.0:
		var elapsed: float = VERTICAL_TRAIN_PROMPT_FLASH_DURATION - vertical_train_prompt_flash_timer
		var blink: float = 0.5 + (0.5 * sin(elapsed * 16.0))
		var flash_tint: Color = Color(1.0, 0.96, 0.58, 1.0)
		player.modulate = base_tint.lerp(flash_tint, clamp(blink, 0.0, 1.0))
	else:
		player.modulate = base_tint

func _update_vertical_train_level(delta: float) -> void:
	if game_state != GameState.PLAYING:
		return

	if vertical_train_cycle_time <= 0.0:
		vertical_train_cycle_time = 0.0
		vertical_train_prompt_flash_timer = VERTICAL_TRAIN_START_FLASH_DURATION
		vertical_train_prompt_should_repeat = true
		vertical_train_prompt_idle_timer = 0.0
		vertical_train_auto_jump_triggered = false
		_emit_vertical_train_start_label()

	vertical_train_cycle_time += delta
	if vertical_train_cycle_time < VERTICAL_TRAIN_START_FLASH_DURATION:
		vertical_train_prompt_flash_timer = max(0.0, VERTICAL_TRAIN_START_FLASH_DURATION - vertical_train_cycle_time)
		vertical_train_arrow_flash_timer = 0.0
		vertical_train_score_flash_timer = 0.0
		_update_vertical_train_start_visuals(delta)
	elif vertical_train_cycle_time < VERTICAL_TRAIN_TASK_PHASE_END:
		vertical_train_prompt_flash_timer = 0.0
		vertical_train_prompt_idle_timer = 0.0
		vertical_train_arrow_flash_timer = max(0.0, VERTICAL_TRAIN_TASK_PHASE_END - vertical_train_cycle_time)
		_vertical_train_update_arrow_flash(delta)
		if vertical_train_arrow_indicator_host == null or not is_instance_valid(vertical_train_arrow_indicator_host):
			_vertical_train_refresh_arrow_indicator()
	elif vertical_train_cycle_time < VERTICAL_TRAIN_JUMP_PHASE_END:
		vertical_train_arrow_flash_timer = max(0.0, VERTICAL_TRAIN_JUMP_PHASE_END - vertical_train_cycle_time)
		_vertical_train_update_arrow_flash(delta)
		if not vertical_train_auto_jump_triggered:
			_vertical_train_trigger_auto_jump()
		_update_vertical_train_jump_visuals(delta)
	elif vertical_train_cycle_time < VERTICAL_TRAIN_SCORE_PHASE_END:
		vertical_train_score_flash_timer = max(0.0, VERTICAL_TRAIN_SCORE_PHASE_END - vertical_train_cycle_time)
		_vertical_train_update_score_phase(delta)
	else:
		_update_vertical_train_rest_visuals(delta)
		if vertical_train_cycle_time >= VERTICAL_TRAIN_CYCLE_DURATION:
			_vertical_train_restart_cycle()

func _update_vertical_train_start_visuals(delta: float) -> void:
	# 开始阶段的视觉效果（提示闪烁）
	if player == null:
		return
	var t: float = Time.get_ticks_msec() / 1000.0
	var intensity: float = 0.5 + 0.5 * sin(t * 12.0)
	player.modulate = Color(brightness, brightness, brightness, 1.0).lerp(Color(1.0, 1.0, 0.6, 1.0), intensity)

func _update_vertical_train_jump_visuals(delta: float) -> void:
	# 跳跃阶段的视觉效果（例如高亮）
	if player == null:
		return
	player.modulate = Color(1.0, 0.9, 0.7, 1.0)

func _update_vertical_train_rest_visuals(delta: float) -> void:
	# 恢复阶段（正常颜色）
	if player == null:
		return
	player.modulate = Color(brightness, brightness, brightness, 1.0)
	、
func _execute_vertical_train_jump(direction: int) -> void:
	if vertical_train_jump_locked or player.is_airborne or vertical_train_fail_pending:
		return
	if direction == 0:
		return
	if vertical_train_current_platform == null or not is_instance_valid(vertical_train_current_platform):
		return
	if vertical_train_next_platform == null or not is_instance_valid(vertical_train_next_platform):
		return
	var delta_x: float = vertical_train_next_platform.global_position.x - vertical_train_current_platform.global_position.x
	var expected_direction: int = -1 if delta_x < 0.0 else 1
	if direction != expected_direction:
		_fail_vertical_train_run()
		return
	var jump_horizontal_speed: float = abs(delta_x) / VERTICAL_TRAIN_JUMP_DURATION
	var jump_vertical_speed: float = max(120.0, (player.gravity * 0.5) - VERTICAL_TRAIN_LAYER_GAP)
	if not player.launch_fixed_jump(float(direction), jump_horizontal_speed, jump_vertical_speed):
		return
	vertical_train_prompt_idle_timer = 0.0
	vertical_train_prompt_should_repeat = true
	vertical_train_expected_platform = vertical_train_next_platform
	vertical_train_jump_locked = true

func _try_land_on_platform_vertical_train(previous_feet_y: float, current_feet_y: float) -> void:
	var candidates: Array[Platform] = []
	if vertical_train_current_platform != null and is_instance_valid(vertical_train_current_platform):
		candidates.append(vertical_train_current_platform)
	if vertical_train_next_platform != null and is_instance_valid(vertical_train_next_platform):
		candidates.append(vertical_train_next_platform)
	if candidates.is_empty():
		return

	var platform: Platform = null
	var best_overlap: float = -1.0
	var best_vertical_delta: float = INF
	for candidate: Platform in candidates:
		var top_y_candidate: float = candidate.top_y()
		var within_vertical: bool = previous_feet_y <= top_y_candidate + LANDING_Y_SNAP and current_feet_y >= top_y_candidate - LANDING_Y_SNAP
		if not within_vertical:
			continue
		var overlap_width: float = candidate.support_overlap_width(player.global_position.x, Player.HALF_SIZE, LANDING_X_MARGIN)
		if overlap_width < MIN_STABLE_SUPPORT_WIDTH:
			continue
		var vertical_delta: float = abs(current_feet_y - top_y_candidate)
		if overlap_width > best_overlap or (is_equal_approx(overlap_width, best_overlap) and vertical_delta < best_vertical_delta):
			platform = candidate
			best_overlap = overlap_width
			best_vertical_delta = vertical_delta

	if platform == null:
		return

	var top_y: float = platform.top_y()
	var landed_on_next: bool = platform == vertical_train_next_platform
	player.land_on(top_y)
	var clamp_min_x: float = platform.left_edge() + Player.HALF_SIZE + LANDING_X_CLAMP_PADDING
	var clamp_max_x: float = platform.right_edge() - Player.HALF_SIZE - LANDING_X_CLAMP_PADDING
	if clamp_min_x <= clamp_max_x:
		player.global_position.x = clamp(player.global_position.x, clamp_min_x, clamp_max_x)
	standing_platform = platform
	standing_platform_last_x = platform.global_position.x
	vertical_train_expected_platform = null
	vertical_train_jump_locked = false
	vertical_train_fail_pending = false

	if landed_on_next:
		if vertical_train_current_platform != null and is_instance_valid(vertical_train_current_platform) and vertical_train_current_platform != platform:
			vertical_train_current_platform.queue_free()
		vertical_train_current_platform = platform
		vertical_train_next_platform = null
		vertical_train_row_index += 1
		score = vertical_train_row_index
		_play_land_sfx()
		vertical_train_score_flash_timer = 1.0
		_play_vertical_train_cheer_sfx()
		if vertical_train_row_index >= VERTICAL_TRAIN_TOTAL_LAYERS:
			_complete_vertical_train_run()
			return
		_spawn_vertical_train_next_platform()
		vertical_train_cycle_time = 0.0
		vertical_train_auto_jump_triggered = false
		vertical_train_prompt_flash_timer = 0.0
		vertical_train_prompt_idle_timer = 0.0
		vertical_train_arrow_flash_timer = 0.0
		vertical_train_prompt_should_repeat = true
		_emit_vertical_train_start_label()
	else:
		score = vertical_train_row_index
		_play_land_sfx()
		vertical_train_cycle_time = 0.0
		vertical_train_auto_jump_triggered = false
		vertical_train_prompt_flash_timer = 0.0
		vertical_train_prompt_idle_timer = 0.0
		vertical_train_arrow_flash_timer = 0.0
		vertical_train_prompt_should_repeat = true
		_emit_vertical_train_start_label()

func _fail_vertical_train_run() -> void:
	if vertical_train_fail_pending:
		return
	vertical_train_fail_pending = true
	vertical_train_fail_timer = 0.55
	player.fail_vertical_lr_fall()
	vertical_train_expected_platform = null
	vertical_train_jump_locked = true
	standing_platform = null
	standing_platform_last_x = 0.0
	_play_fail_sfx()

func _finalize_vertical_train_fail() -> void:
	vertical_train_fail_pending = false
	vertical_train_jump_locked = false
	if vertical_train_current_platform != null and is_instance_valid(vertical_train_current_platform):
		player.reset_to_platform(vertical_train_current_platform)
		standing_platform = vertical_train_current_platform
		standing_platform_last_x = vertical_train_current_platform.global_position.x
		score = vertical_train_row_index
		_play_land_sfx()
		_schedule_vertical_train_prompt(VERTICAL_TRAIN_PROMPT_TRIGGER_DELAY_RETURN)
		_refresh_ui()
	else:
		game_state = GameState.GAME_OVER
		wait_for_accept_release = true
		_save_record(score)
		_save_settings()
		_update_records_display()
		_refresh_ui()

func _complete_vertical_train_run() -> void:
	vertical_train_completion_time = (Time.get_ticks_msec() / 1000.0) - vertical_train_start_time
	vertical_train_fail_pending = false
	vertical_train_jump_locked = false
	score = vertical_train_row_index
	game_state = GameState.GAME_OVER
	wait_for_accept_release = true
	_save_record("%.1fs" % vertical_train_completion_time)
	_save_settings()
	_update_records_display()
	_refresh_ui()

func _complete_vertical_lr_run() -> void:
	if vertical_lr_finished:
		return
	vertical_lr_finished = true
	vertical_lr_success = true
	vertical_lr_expected_platform = null
	vertical_lr_left_option = null
	vertical_lr_right_option = null
	vertical_lr_completion_time = (Time.get_ticks_msec() / 1000.0) - vertical_lr_start_time
	game_state = GameState.GAME_OVER
	wait_for_accept_release = true
	_save_record(score)
	_save_settings()
	_update_records_display()
	_refresh_ui()

func _fail_vertical_lr_run() -> void:
	if vertical_lr_finished:
		return
	if vertical_lr_fail_pending:
		return
	vertical_lr_fail_pending = true
	vertical_lr_success = false
	vertical_lr_fail_timer = 0.55
	vertical_lr_completion_time = (Time.get_ticks_msec() / 1000.0) - vertical_lr_start_time
	player.fail_vertical_lr_fall()
	vertical_lr_expected_platform = null
	vertical_lr_jump_locked = true
	vertical_lr_left_option = null
	vertical_lr_right_option = null
	perfect_combo_streak = 0
	standing_platform = null
	standing_platform_last_x = 0.0
	_play_fail_sfx()

func _finalize_vertical_lr_fail() -> void:
	if vertical_lr_finished:
		return
	vertical_lr_finished = true
	vertical_lr_fail_pending = false
	vertical_lr_jump_locked = false
	game_state = GameState.GAME_OVER
	wait_for_accept_release = true
	_save_record(score)
	_save_settings()
	_update_records_display()
	_refresh_ui()

func _ensure_ground_support() -> void:
	var best_platform: Platform = null
	var best_overlap: float = -1.0
	var second_overlap: float = -1.0

	for child: Node in platforms_root.get_children():
		var platform: Platform = child as Platform
		if platform == null:
			continue
		if not platform.can_support_landing():
			continue

		var close_to_surface: bool = abs(player.feet_y() - platform.top_y()) <= LANDING_Y_SNAP + 3.0
		if not close_to_surface:
			continue

		var overlap: float = platform.support_overlap_width(player.global_position.x, Player.HALF_SIZE, 0.0)
		if overlap > best_overlap:
			second_overlap = best_overlap
			best_overlap = overlap
			best_platform = platform
		elif overlap > second_overlap:
			second_overlap = overlap

	if best_platform == null or best_overlap < MIN_STABLE_SUPPORT_WIDTH:
		player.drop_from_platform()
		standing_platform = null
		standing_platform_last_x = 0.0
		return

	# If two platforms support almost equally and neither is dominant, treat it as unstable gap support.
	if second_overlap >= 0.0 and abs(best_overlap - second_overlap) <= AMBIGUOUS_SUPPORT_DIFF and best_overlap < MIN_DOMINANT_SUPPORT_WIDTH:
		player.drop_from_platform()
		standing_platform = null
		standing_platform_last_x = 0.0
		return

	if standing_platform != null and is_instance_valid(standing_platform) and standing_platform == best_platform:
		player.global_position.x += best_platform.global_position.x - standing_platform_last_x
	standing_platform_last_x = best_platform.global_position.x
	standing_platform = best_platform
	player.global_position.y = best_platform.top_y() - Player.HALF_SIZE

func _difficulty_ratio() -> float:
	var local_ratio: float = clamp(float(score) / DIFFICULTY_SCORE_TARGET, 0.0, 1.0)
	if realtime_difficulty_scale >= 0.0:
		return clamp((local_ratio * 0.55) + (realtime_difficulty_scale * 0.45), 0.0, 1.0)
	return local_ratio

func _update_realtime_bridge(delta: float) -> void:
	if realtime_ws == null:
		realtime_ws = WebSocketPeer.new()

	var state: WebSocketPeer.State = realtime_ws.get_ready_state()
	if state == WebSocketPeer.STATE_OPEN:
		realtime_ws.poll()
		while realtime_ws.get_available_packet_count() > 0:
			var packet: PackedByteArray = realtime_ws.get_packet()
			var parsed: Variant = JSON.parse_string(packet.get_string_from_utf8())
			if parsed is Dictionary:
				var payload: Dictionary = parsed
				var difficulty_value: Variant = payload.get("difficulty_scale", null)
				var airborne_bonus_value: Variant = payload.get("airborne_bonus", 0.0)
				if difficulty_value is float or difficulty_value is int:
					var difficulty_num: float = float(difficulty_value)
					var bonus_num: float = float(airborne_bonus_value) if (airborne_bonus_value is float or airborne_bonus_value is int) else 0.0
					realtime_difficulty_scale = clamp(difficulty_num + bonus_num, 0.0, 1.0)

		realtime_send_cooldown -= delta
		if realtime_send_cooldown <= 0.0:
			realtime_send_cooldown = REALTIME_SEND_INTERVAL
			var payload_out: Dictionary = {
				"score": score,
				"airborne": player.is_airborne,
				"charging": player.is_charging,
				"time": Time.get_ticks_msec()
			}
			realtime_ws.send_text(JSON.stringify(payload_out))
		return

	if state == WebSocketPeer.STATE_CONNECTING:
		realtime_ws.poll()
		return

	realtime_reconnect_cooldown -= delta
	if realtime_reconnect_cooldown > 0.0:
		return

	realtime_reconnect_cooldown = REALTIME_RECONNECT_INTERVAL
	realtime_difficulty_scale = -1.0
	if realtime_ws.get_ready_state() != WebSocketPeer.STATE_CLOSED:
		realtime_ws.close()
	realtime_ws = WebSocketPeer.new()
	realtime_ws.connect_to_url(REALTIME_WS_URL)

func _update_mi_bridge(delta: float) -> void:
	if current_control_mode != ControlMode.MI:
		if mi_ws != null and mi_ws.get_ready_state() == WebSocketPeer.STATE_OPEN:
			mi_ws.close()
		return

	if mi_ws == null:
		mi_ws = WebSocketPeer.new()

	var state: WebSocketPeer.State = mi_ws.get_ready_state()
	if state == WebSocketPeer.STATE_OPEN:
		mi_ws.poll()
		if mi_ws.get_ready_state() != WebSocketPeer.STATE_OPEN:
			return
		while mi_ws.get_available_packet_count() > 0:
			var packet: PackedByteArray = mi_ws.get_packet()
			_process_mi_packet(packet.get_string_from_utf8())
		mi_status_send_cooldown -= delta
		if mi_status_send_cooldown <= 0.0:
			mi_status_send_cooldown = MI_STATUS_SEND_INTERVAL
			var status_payload: Dictionary = {
				"type": "mi_status",
				"timestamp_ms": int(Time.get_unix_time_from_system() * 1000.0),
				"score": score,
				"airborne": player.is_airborne,
				"charging": player.is_charging,
				"mi_state": mi_state,
				"control_mode": current_control_mode,
				"mi_input_mode": current_mi_input_mode
			}
			if mi_ws.get_ready_state() == WebSocketPeer.STATE_OPEN:
				var send_result: int = mi_ws.send_text(JSON.stringify(status_payload))
				if send_result != OK:
					mi_reconnect_cooldown = 0.0
					if mi_ws.get_ready_state() != WebSocketPeer.STATE_CLOSED:
						mi_ws.close()
		return

	if state == WebSocketPeer.STATE_CONNECTING:
		mi_ws.poll()
		return

	mi_reconnect_cooldown -= delta
	if mi_reconnect_cooldown > 0.0:
		return

	mi_reconnect_cooldown = MI_RECONNECT_INTERVAL
	if mi_ws.get_ready_state() != WebSocketPeer.STATE_CLOSED:
		mi_ws.close()
	mi_ws = WebSocketPeer.new()
	mi_last_seq = -1
	var target_url: String = mi_offline_ws_url if current_mi_input_mode == MIInputMode.OFFLINE else mi_online_ws_url
	mi_ws.connect_to_url(target_url)

func _process_mi_packet(raw_text: String) -> void:
	var parsed: Variant = JSON.parse_string(raw_text)
	if not (parsed is Dictionary):
		return
	var data: Dictionary = parsed

	var seq_variant: Variant = _packet_pick(data, MI_SEQ_FIELD_CANDIDATES, null)
	var seq: int = mi_last_seq + 1
	if seq_variant != null:
		seq = int(seq_variant)
		if seq <= mi_last_seq:
			# Allow sender restart in offline tests where sequence often resets to 1.
			if seq == 1:
				mi_last_seq = 0
			else:
				mi_out_of_order_dropped += 1
				return
	mi_last_seq = seq

	var now_ms: int = int(Time.get_unix_time_from_system() * 1000.0)
	var ts_variant: Variant = _packet_pick(data, MI_TIMESTAMP_FIELD_CANDIDATES, now_ms)
	var ts_ms: int = _normalize_timestamp_ms(ts_variant, now_ms)
	if abs(now_ms - ts_ms) > MI_PACKET_TTL_MS:
		mi_stale_dropped += 1
		return

	mi_messages_received += 1
	var lag_ms: float = float(max(0, now_ms - ts_ms))
	mi_latency_ms_ema = lag_ms if is_zero_approx(mi_latency_ms_ema) else lerp(mi_latency_ms_ema, lag_ms, 0.18)

	var label: String = _normalize_packet_label(data)
	var confidence: float = clamp(float(_packet_pick(data, MI_CONFIDENCE_FIELD_CANDIDATES, 1.0)), 0.0, 1.0)
	_process_mi_signal(label, confidence)

func _packet_pick(data: Dictionary, keys: Array[String], fallback: Variant) -> Variant:
	for key: String in keys:
		if data.has(key):
			return data.get(key)
	return fallback

func _normalize_timestamp_ms(raw_value: Variant, fallback_now_ms: int) -> int:
	if raw_value is int or raw_value is float:
		var numeric: float = float(raw_value)
		# Heuristic: treat second-level timestamps as milliseconds.
		if numeric > 0.0 and numeric < 1000000000000.0:
			numeric *= 1000.0
		return int(numeric)
	return fallback_now_ms

func _normalize_packet_label(data: Dictionary) -> String:
	var raw_label: String = str(_packet_pick(data, MI_LABEL_FIELD_CANDIDATES, "")).strip_edges().to_lower()
	if raw_label == "":
		var class_variant: Variant = _packet_pick(data, MI_CLASS_ID_FIELD_CANDIDATES, null)
		if class_variant != null:
			var mapped: Variant = mi_class_id_to_label.get(int(class_variant), "")
			if mapped == "":
				mapped = mi_class_id_to_label.get(str(class_variant), "")
			raw_label = str(mapped).strip_edges().to_lower()

	# For Vertical LR/Training modes, map left_hand/right_hand to left/right
	if current_mode == GameMode.VERTICAL_LR or current_mode == GameMode.VERTICAL_TRAIN:
		if raw_label == "left_hand" or raw_label == "left" or raw_label == "lh":
			return "left"
		if raw_label == "right_hand" or raw_label == "right" or raw_label == "rh":
			return "right"
		if raw_label == "rest" or raw_label == "idle" or raw_label == "none" or raw_label == "neutral":
			return "rest"
		return "rest"
	
	# For Classic and Race modes, use hand/foot/rest mapping
	if raw_label == "hand" or raw_label == "right_hand" or raw_label == "right" or raw_label == "rh":
		return "hand"
	if raw_label == "foot" or raw_label == "feet" or raw_label == "left_hand" or raw_label == "left" or raw_label == "lh":
		return "foot"
	if raw_label == "rest" or raw_label == "idle" or raw_label == "none" or raw_label == "neutral":
		return "rest"
	return "rest"

func _process_mi_signal(label: String, confidence: float) -> void:
	if current_mode == GameMode.VERTICAL_LR or current_mode == GameMode.VERTICAL_TRAIN:
		# For vertical LR mode, use left/right labels directly
		var effective_label: String = "rest"
		if label == "left" and confidence >= MI_HAND_CONF_THRESHOLD:
			effective_label = "left"
		elif label == "right" and confidence >= MI_HAND_CONF_THRESHOLD:
			effective_label = "right"
		elif label == "rest":
			effective_label = "rest"
		
		if effective_label == mi_raw_label:
			mi_raw_streak += 1
		else:
			mi_raw_label = effective_label
			mi_raw_streak = 1
		
		var needed: int = 1  # For vertical mode, accept immediately
		if mi_raw_streak >= needed and mi_decision_label != effective_label:
			mi_decision_label = effective_label
		return
	
	# Original logic for Classic and Race modes
	var effective_label: String = "rest"
	if label == "hand" and confidence >= MI_HAND_CONF_THRESHOLD:
		effective_label = "hand"
	elif label == "foot" and confidence >= MI_FOOT_CONF_THRESHOLD:
		effective_label = "foot"

	if effective_label == mi_raw_label:
		mi_raw_streak += 1
	else:
		mi_raw_label = effective_label
		mi_raw_streak = 1

	var needed: int = _mi_needed_count(effective_label)
	if effective_label == "rest":
		needed = 1
	if mi_raw_streak >= needed and mi_decision_label != effective_label:
		mi_decision_label = effective_label

func _mi_needed_count(effective_label: String) -> int:
	if effective_label == "rest":
		return 1
	if current_mi_input_mode == MIInputMode.OFFLINE:
		return 1
	if effective_label == "hand":
		return MI_HAND_CONFIRM_COUNT
	if effective_label == "foot":
		return MI_FOOT_CONFIRM_COUNT
	return 1

func _mi_reset_decision_tracking() -> void:
	mi_decision_label = "none"
	mi_raw_label = "none"
	mi_raw_streak = 0

func _reset_mi_runtime_state() -> void:
	mi_state = MIState.IDLE
	mi_keepalive_timer = 0.0
	mi_air_jump_used = false
	mi_last_action_time = -10.0
	mi_last_air_jump_time = -10.0
	mi_hand_activation_timer = 0.0
	mi_raw_label = "none"
	mi_raw_streak = 0
	mi_decision_label = "none"
	input_action_pending = InputAction.NONE
	mi_status_send_cooldown = 0.0
	player.cancel_charge()
	player.always_show_charge_bar = current_control_mode == ControlMode.MANUAL

func _roll_platform_kind(difficulty: float, allow_special: bool) -> Platform.PlatformKind:
	if not allow_special:
		return Platform.PlatformKind.NORMAL
	var special_chance: float = lerp(SPECIAL_BASE_CHANCE, SPECIAL_MAX_CHANCE, difficulty)
	if rng.randf() > special_chance:
		return Platform.PlatformKind.NORMAL

	var roll: float = rng.randf()
	var moving_weight: float = lerp(0.45, 0.32, difficulty)
	if roll < moving_weight:
		return Platform.PlatformKind.MOVING
	return Platform.PlatformKind.FRAGILE

func _show_landing_feedback(is_perfect: bool, bonus: int, landing_score: int) -> void:
	if is_perfect:
		if perfect_combo_streak >= 2:
			feedback_text = _t("feedback_perfect_combo") % landing_score
		else:
			feedback_text = _t("feedback_perfect") % landing_score
	else:
		feedback_text = _t("feedback_land") % landing_score
	if bonus > 0:
		feedback_text += " " + (_t("feedback_risk") % bonus)
	feedback_timer = FEEDBACK_SHOW_TIME

func _follow_camera(delta: float) -> void:
	if current_mode == GameMode.VERTICAL_LR or current_mode == GameMode.VERTICAL_TRAIN:
		# Vertical LR mode: follow player's Y position
		var current_y: float = camera_2d.global_position.y
		var target_y: float = max(current_y, player.global_position.y + 100.0)
		var blend: float = 1.0 - exp(-CAMERA_FOLLOW_SMOOTHNESS * delta)
		var smoothed_target_y: float = lerp(current_y, target_y, blend)
		var max_step: float = CAMERA_MAX_SCROLL_SPEED * delta
		var step: float = min(smoothed_target_y - current_y, max_step)
		camera_2d.global_position.y = current_y + max(0.0, step)
		# Keep X centered on player
		camera_2d.global_position.x = player.global_position.x
	# focus mode removed: no special camera follow
	else:
		# Classic and Race modes: follow X position
		var current_x: float = camera_2d.global_position.x
		var target_x: float = max(current_x, player.global_position.x + CAMERA_LEAD_X)
		var blend: float = 1.0 - exp(-CAMERA_FOLLOW_SMOOTHNESS * delta)
		var smoothed_target_x: float = lerp(current_x, target_x, blend)
		var max_step: float = CAMERA_MAX_SCROLL_SPEED * delta
		var step: float = min(smoothed_target_x - current_x, max_step)
		camera_2d.global_position.x = current_x + max(0.0, step)
		camera_2d.global_position.y = CAMERA_FIXED_Y


func _check_game_over() -> void:
	if game_state != GameState.PLAYING:
		return
	
	# Vertical LR mode has its own game-over logic in _physics_process
	if current_mode == GameMode.VERTICAL_LR or current_mode == GameMode.VERTICAL_TRAIN:
		return
	
	var viewport_size: Vector2 = get_viewport_rect().size
	var bottom_limit: float = camera_2d.global_position.y + viewport_size.y * 0.5 + 80.0
	if player.global_position.y > bottom_limit:
		game_state = GameState.GAME_OVER
		wait_for_accept_release = true
		perfect_combo_streak = 0
		standing_platform = null
		standing_platform_last_x = 0.0
		_save_record(score)
		_save_settings()
		_update_records_display()
		_play_fail_sfx()

func _adjust_brightness(amount: float) -> void:
	brightness = clamp(brightness + amount, BRIGHTNESS_MIN, BRIGHTNESS_MAX)
	_apply_brightness()
	_save_settings()
	_refresh_ui()

func _apply_brightness() -> void:
	var tint: Color = Color(brightness, brightness, brightness, 1.0)
	platforms_root.modulate = tint
	player.modulate = tint

func _adjust_sfx_volume(amount: float) -> void:
	sfx_volume = clamp(sfx_volume + amount, SFX_VOLUME_MIN, SFX_VOLUME_MAX)
	_apply_sfx_volume()
	_save_settings()
	_refresh_ui()

func _register_perfect_count() -> void:
	if current_mode != GameMode.CLASSIC:
		return
	perfect_count_in_run += 1
	perfect_count_label.text = _t("perfect_count") % perfect_count_in_run
	perfect_count_label.visible = true
	perfect_display_timer += PERFECT_DISPLAY_EXTEND
	perfect_idle_timer = 0.0

func _register_jump_combo() -> void:
	if current_mode != GameMode.CLASSIC:
		return
	var now_sec: float = Time.get_ticks_msec() / 1000.0
	if last_jump_time_sec < 0.0 or now_sec - last_jump_time_sec > COMBO_INTERVAL_LIMIT:
		combo_count = 1
	else:
		combo_count += 1
	last_jump_time_sec = now_sec
	combo_label.text = _t("combo") % combo_count
	combo_label.visible = true
	combo_display_timer = COMBO_DISPLAY_TIME

func _apply_sfx_volume() -> void:
	var db: float = linear_to_db(max(0.001, sfx_volume))
	if sfx_land_player != null:
		sfx_land_player.volume_db = db
	if sfx_perfect_player != null:
		sfx_perfect_player.volume_db = db
	if sfx_fail_player != null:
		sfx_fail_player.volume_db = db
	if sfx_charge_player != null:
		sfx_charge_player.volume_db = db
	if sfx_train_cheer_player != null:
		sfx_train_cheer_player.volume_db = db

func _setup_sfx_players() -> void:
	sfx_land_player = _create_sfx_player("SfxLand")
	sfx_perfect_player = _create_sfx_player("SfxPerfect")
	sfx_fail_player = _create_sfx_player("SfxFail")
	sfx_charge_player = _create_sfx_player("SfxCharge")
	sfx_train_cheer_player = _create_sfx_player("SfxTrainCheer")

func _create_sfx_player(player_name: String) -> AudioStreamPlayer:
	var player_node: AudioStreamPlayer = AudioStreamPlayer.new()
	player_node.name = player_name
	var generator: AudioStreamGenerator = AudioStreamGenerator.new()
	generator.mix_rate = SFX_SAMPLE_RATE
	generator.buffer_length = SFX_BUFFER_LENGTH
	player_node.stream = generator
	add_child(player_node)
	return player_node

func _play_pattern(player_node: AudioStreamPlayer, notes: Array, volume: float) -> void:
	if player_node == null:
		return
	var generator: AudioStreamGenerator = player_node.stream as AudioStreamGenerator
	if generator == null:
		return
	player_node.stop()
	player_node.play()
	var playback: AudioStreamGeneratorPlayback = player_node.get_stream_playback() as AudioStreamGeneratorPlayback
	if playback == null:
		return
	for note in notes:
		var freq: float = note.x
		var duration: float = note.y
		var frame_count: int = max(1, int(duration * generator.mix_rate))
		for i: int in range(frame_count):
			var t: float = float(i) / generator.mix_rate
			var progress: float = float(i) / float(frame_count)
			var env: float = pow(1.0 - progress, 1.9) * sin(PI * progress)
			var fundamental: float = sin(TAU * freq * t)
			var harmonic: float = 0.18 * sin(TAU * freq * 2.0 * t)
			var sample: float = (fundamental + harmonic) * env * volume
			playback.push_frame(Vector2(sample, sample))

func _play_land_sfx() -> void:
	_play_pattern(sfx_land_player, [Vector2(360.0, 0.07), Vector2(430.0, 0.06)], 0.22)

func _play_perfect_land_sfx() -> void:
	_play_pattern(sfx_perfect_player, [Vector2(460.0, 0.07), Vector2(560.0, 0.07), Vector2(660.0, 0.08)], 0.24)

func _play_fail_sfx() -> void:
	_play_pattern(sfx_fail_player, [Vector2(300.0, 0.08), Vector2(230.0, 0.1), Vector2(180.0, 0.13)], 0.25)

func _play_charge_ready_sfx() -> void:
	_play_pattern(sfx_charge_player, [Vector2(690.0, 0.045)], 0.2)

func _load_records() -> void:
	recent_records.clear()
	if not FileAccess.file_exists(RECORDS_FILE_PATH):
		_update_records_display()
		return
	var file: FileAccess = FileAccess.open(RECORDS_FILE_PATH, FileAccess.READ)
	if file == null:
		_update_records_display()
		return
	var raw: String = file.get_as_text()
	file.close()
	var parsed: Variant = JSON.parse_string(raw)
	if parsed is Array:
		recent_records = parsed
	if recent_records.size() > MAX_RECORDS:
		recent_records = recent_records.slice(0, MAX_RECORDS)
	_update_records_display()

func _load_settings() -> void:
	if not FileAccess.file_exists(SETTINGS_FILE_PATH):
		return
	var file: FileAccess = FileAccess.open(SETTINGS_FILE_PATH, FileAccess.READ)
	if file == null:
		return
	var raw: String = file.get_as_text()
	file.close()
	var parsed: Variant = JSON.parse_string(raw)
	if not (parsed is Dictionary):
		return
	var data: Dictionary = parsed
	brightness = clamp(float(data.get("brightness", brightness)), BRIGHTNESS_MIN, BRIGHTNESS_MAX)
	sfx_volume = clamp(float(data.get("sfx_volume", sfx_volume)), SFX_VOLUME_MIN, SFX_VOLUME_MAX)
	var saved_lang: String = str(data.get("language", current_language))
	if saved_lang == "zh" or saved_lang == "en":
		current_language = saved_lang
	var saved_mode: String = str(data.get("mode", "classic"))
	if saved_mode == "race":
		current_mode = GameMode.RACE
	elif saved_mode == "vertical_lr":
		current_mode = GameMode.VERTICAL_LR
	elif saved_mode == "vertical_train":
		current_mode = GameMode.VERTICAL_TRAIN
	else:
		current_mode = GameMode.CLASSIC
	var saved_control: String = str(data.get("control_mode", "manual"))
	current_control_mode = ControlMode.MI if saved_control == "mi" else ControlMode.MANUAL
	var saved_mi_input: String = str(data.get("mi_input_mode", "offline"))
	current_mi_input_mode = MIInputMode.ONLINE if saved_mi_input == "online" else MIInputMode.OFFLINE
	mi_offline_ws_url = str(data.get("mi_offline_ws_url", MI_OFFLINE_WS_URL))
	mi_online_ws_url = str(data.get("mi_online_ws_url", MI_ONLINE_WS_URL))
	var class_map_data: Variant = data.get("mi_class_id_to_label", mi_class_id_to_label)
	if class_map_data is Dictionary:
		mi_class_id_to_label = _sanitize_mi_class_map(class_map_data)
	var saved_duration: int = int(data.get("race_duration", RACE_DURATION_DEFAULT))
	race_duration_seconds = RACE_DURATION_DEFAULT
	for item: int in RACE_DURATION_OPTIONS:
		if item == saved_duration:
			race_duration_seconds = item
			break
	var saved_name: String = str(data.get("player_name", "Player"))
	if saved_name != "":
		player_name_edit.text = saved_name

func _save_settings() -> void:
	var data: Dictionary = {
		"brightness": brightness,
		"sfx_volume": sfx_volume,
		"language": current_language,
		"control_mode": "mi" if current_control_mode == ControlMode.MI else "manual",
		"mi_input_mode": "online" if current_mi_input_mode == MIInputMode.ONLINE else "offline",
		"mi_offline_ws_url": mi_offline_ws_url,
		"mi_online_ws_url": mi_online_ws_url,
		"mi_class_id_to_label": mi_class_id_to_label,
		"mode": "race" if current_mode == GameMode.RACE else "vertical_lr" if current_mode == GameMode.VERTICAL_LR else "vertical_train" if current_mode == GameMode.VERTICAL_TRAIN else "classic",
		"race_duration": race_duration_seconds,
		"player_name": player_name_edit.text.strip_edges()
	}
	var file: FileAccess = FileAccess.open(SETTINGS_FILE_PATH, FileAccess.WRITE)
	if file != null:
		file.store_string(JSON.stringify(data))
		file.close()

func _sanitize_mi_class_map(raw_map: Dictionary) -> Dictionary:
	var sanitized: Dictionary = MI_CLASS_ID_TO_LABEL_DEFAULT.duplicate(true)
	for key: Variant in raw_map.keys():
		var mapped: String = str(raw_map.get(key, "")).strip_edges().to_lower()
		if mapped == "":
			continue
		if mapped != "hand" and mapped != "foot" and mapped != "rest":
			continue
		sanitized[key] = mapped
	return sanitized

func _save_record(final_score) -> void:
	var player_name: String = player_name_edit.text.strip_edges()
	if player_name == "":
		player_name = _t("default_player")
	var record: Dictionary = {
		"time": _now_text(),
		"player": player_name,
		"score": final_score
	}
	recent_records.push_front(record)
	if recent_records.size() > MAX_RECORDS:
		recent_records = recent_records.slice(0, MAX_RECORDS)
	var file: FileAccess = FileAccess.open(RECORDS_FILE_PATH, FileAccess.WRITE)
	if file != null:
		file.store_string(JSON.stringify(recent_records))
		file.close()

func _now_text() -> String:
	var d: Dictionary = Time.get_datetime_dict_from_system()
	return "%04d-%02d-%02d %02d:%02d:%02d" % [
		int(d.get("year", 2026)),
		int(d.get("month", 1)),
		int(d.get("day", 1)),
		int(d.get("hour", 0)),
		int(d.get("minute", 0)),
		int(d.get("second", 0))
	]

func _update_records_display() -> void:
	if records_label == null:
		return
	if recent_records.is_empty():
		records_label.text = _t("records_empty")
		return
	var lines: Array[String] = []
	for i: int in range(recent_records.size()):
		var item: Dictionary = recent_records[i]
		var time_text: String = str(item.get("time", "----"))
		var player_text: String = str(item.get("player", _t("default_player")))
		var score_text: String = str(item.get("score", 0))
		lines.append(_t("record_line") % [i + 1, time_text, player_text, score_text])
	records_label.text = "\n".join(lines)

func _refresh_ui() -> void:
	if current_mode == GameMode.RACE:
		score_label.text = "%s: %d" % [_t("distance"), score]
	
	elif current_mode == GameMode.VERTICAL_LR:
		score_label.text = "%s: %d" % [_t("score"), score]
	elif current_mode == GameMode.VERTICAL_TRAIN:
		score_label.text = "%s: %d" % [_t("layer"), score]
	else:
		score_label.text = "%s: %d" % [_t("score"), score]
	
	brightness_label.text = "%s: %d%% (-/+)" % [_t("brightness"), int(brightness * 100.0)]
	volume_label.text = "%s: %d%% ([/])" % [_t("volume"), int(sfx_volume * 100.0)]
	language_label.text = _t("language")
	control_label.text = _t("control")
	mode_label.text = _t("mode")
	duration_label.text = _t("race_time")
	mi_input_label.text = _t("mi_input")
	control_option.select(0 if current_control_mode == ControlMode.MANUAL else 1)
	mi_input_option.select(0 if current_mi_input_mode == MIInputMode.OFFLINE else 1)
	player_name_edit.placeholder_text = _t("player_name_placeholder")
	records_title.text = _t("records_title")
	start_label.text = _t("start_title")
	
	if current_mode == GameMode.VERTICAL_LR and game_state == GameState.PLAYING:
		race_info_label.text = _t("vertical_lr_trial") % [vertical_lr_time_left, score]
	elif current_mode == GameMode.VERTICAL_LR:
		if vertical_lr_success:
			race_info_label.text = _t("vertical_lr_completion") % vertical_lr_completion_time
		else:
			race_info_label.text = _t("vertical_lr_elapsed") % vertical_lr_completion_time
	elif current_mode == GameMode.VERTICAL_TRAIN and game_state == GameState.PLAYING:
		race_info_label.text = _t("vertical_train_progress") % [vertical_train_row_index, VERTICAL_TRAIN_TOTAL_LAYERS, Time.get_ticks_msec() / 1000.0 - vertical_train_start_time]
	elif current_mode == GameMode.VERTICAL_TRAIN:
		race_info_label.text = _t("vertical_train_progress") % [VERTICAL_TRAIN_TOTAL_LAYERS, VERTICAL_TRAIN_TOTAL_LAYERS, vertical_train_completion_time]
	else:
		race_info_label.text = _t("race_info") % [race_time_left, race_distance]
	
	if realtime_ws != null and realtime_ws.get_ready_state() == WebSocketPeer.STATE_OPEN:
		network_label.text = "%s: %s" % [_t("network"), _t("net_online")]
	elif realtime_ws != null and realtime_ws.get_ready_state() == WebSocketPeer.STATE_CONNECTING:
		network_label.text = "%s: %s" % [_t("network"), _t("net_connecting")]
	else:
		network_label.text = "%s: %s" % [_t("network"), _t("net_offline")]
	
	records_title.visible = game_state != GameState.PLAYING
	records_label.visible = game_state != GameState.PLAYING
	player_name_edit.visible = game_state != GameState.PLAYING
	language_label.visible = game_state != GameState.PLAYING
	language_option.visible = game_state != GameState.PLAYING
	mode_label.visible = game_state != GameState.PLAYING
	mode_option.visible = game_state != GameState.PLAYING
	control_label.visible = game_state != GameState.PLAYING
	control_option.visible = game_state != GameState.PLAYING
	mi_input_label.visible = game_state != GameState.PLAYING and current_control_mode == ControlMode.MI
	mi_input_option.visible = game_state != GameState.PLAYING and current_control_mode == ControlMode.MI
	duration_label.visible = game_state != GameState.PLAYING and current_mode == GameMode.RACE
	duration_option.visible = game_state != GameState.PLAYING and current_mode == GameMode.RACE
	race_info_label.visible = (game_state == GameState.PLAYING and (current_mode == GameMode.RACE or current_mode == GameMode.VERTICAL_LR or current_mode == GameMode.VERTICAL_TRAIN)) or ((current_mode == GameMode.VERTICAL_LR or current_mode == GameMode.VERTICAL_TRAIN) and game_state == GameState.GAME_OVER)
	if platform_minimap != null:
		platform_minimap.visible = current_mode == GameMode.VERTICAL_LR
	
	if game_state != GameState.PLAYING or current_mode != GameMode.CLASSIC:
		perfect_count_label.visible = false
		combo_label.visible = false
	
	start_label.visible = game_state == GameState.START
	
	if game_state == GameState.START:
		state_label.text = _t("state_start")
	elif current_mode == GameMode.VERTICAL_LR and vertical_lr_fail_pending:
		state_label.text = _t("state_vertical_lr_falling")
	elif current_mode == GameMode.VERTICAL_TRAIN and vertical_train_fail_pending:
		state_label.text = _t("state_vertical_train_returning")
	elif game_state == GameState.GAME_OVER:
		if current_mode == GameMode.RACE:
			state_label.text = _t("state_race_over")
		elif current_mode == GameMode.VERTICAL_LR:
			state_label.text = _t("state_vertical_lr_clear") if vertical_lr_success else _t("state_vertical_lr_fail")
		elif current_mode == GameMode.VERTICAL_TRAIN:
			state_label.text = _t("state_vertical_train_clear")
		else:
			state_label.text = _t("state_game_over")
	elif current_mode == GameMode.VERTICAL_LR and game_state == GameState.PLAYING:
		state_label.text = _t("vertical_lr_select")
	elif current_mode == GameMode.VERTICAL_TRAIN and game_state == GameState.PLAYING:
		if vertical_train_prompt_flash_timer > 0.0:
			state_label.text = _t("state_vertical_train_prompt")
		else:
			state_label.text = _t("state_vertical_train_wait")
	elif current_mode == GameMode.CLASSIC and feedback_timer > 0.0 and feedback_text != "":
		state_label.text = feedback_text
	elif current_control_mode == ControlMode.MI:
		if game_state == GameState.PLAYING:
			var mi_state_key: String = "state_mi_idle"
			if mi_state == MIState.CHARGING:
				mi_state_key = "state_mi_charging"
			elif mi_state == MIState.REST_KEEPALIVE:
				mi_state_key = "state_mi_keepalive"
			elif mi_state == MIState.AIRBORNE:
				mi_state_key = "state_mi_airborne"
			state_label.text = _t("mi_metrics") % [mi_messages_received, mi_out_of_order_dropped, mi_stale_dropped, mi_cancel_count, mi_air_jump_count, mi_latency_ms_ema]
			state_label.text += " | " + _t(mi_state_key)
		else:
			state_label.text = _t("state_idle")
	elif player.is_airborne:
		state_label.text = _t("state_flying")
	elif player.is_charging:
		state_label.text = _t("state_charging") % (player.charge_ratio() * 100.0)
	else:
		state_label.text = _t("state_idle")

# focus mode removed: associated functions cleaned up
