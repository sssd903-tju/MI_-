extends CharacterBody2D
class_name Player

const HALF_SIZE: float = 18.0
const BAR_WIDTH: float = 12.0
const BAR_HEIGHT: float = 92.0
const MAX_CHARGE_FLASH_THRESHOLD: float = 0.985
const MAX_COLLISION_ITERATIONS: int = 4
const SIDE_BOUNCE_RATIO: float = 0.18
const UNDERSIDE_PUSH_SPEED: float = 190.0

@export var gravity: float = 1700.0
@export var min_jump_impulse: float = 380.0
@export var max_jump_impulse: float = 980.0
@export var max_charge_time: float = 1.2
@export var vertical_ratio: float = 0.82
@export var squash_strength: float = 0.34
@export var squash_lerp_speed: float = 14.0
@export var launch_stretch_strength: float = 0.22
@export var launch_stretch_duration: float = 0.24
@export var squash_drop_factor: float = 0.72
@export var air_jump_strength_ratio: float = 0.62

var charge_time: float = 0.0
var is_charging: bool = false
var is_airborne: bool = false
var launch_stretch_timer: float = 0.0
var jump_started_this_airborne: bool = false
var charge_paused: bool = false
var always_show_charge_bar: bool = true

@onready var visual: Polygon2D = $Visual
@onready var charge_bar: Node2D = $ChargeBar
@onready var bar_bg: Polygon2D = $ChargeBar/BarBG
@onready var bar_fill: Polygon2D = $ChargeBar/BarFill

var visual_base_position: Vector2 = Vector2.ZERO

func _ready() -> void:
	visual_base_position = visual.position
	bar_bg.polygon = PackedVector2Array([
		Vector2(-BAR_WIDTH * 0.5, 0.0),
		Vector2(BAR_WIDTH * 0.5, 0.0),
		Vector2(BAR_WIDTH * 0.5, -BAR_HEIGHT),
		Vector2(-BAR_WIDTH * 0.5, -BAR_HEIGHT)
	])
	_update_charge_bar()
	_update_visual_feedback(1.0)

func begin_charge() -> void:
	if is_airborne or is_charging:
		return
	is_charging = true
	charge_paused = false
	charge_time = 0.0
	_update_charge_bar()

func resume_charge() -> void:
	if is_airborne:
		return
	if not is_charging:
		is_charging = true
	charge_paused = false
	_update_charge_bar()

func pause_charge() -> void:
	if is_airborne or not is_charging:
		return
	charge_paused = true
	_update_charge_bar()

func cancel_charge() -> void:
	if is_airborne:
		return
	is_charging = false
	charge_paused = false
	charge_time = 0.0
	_update_charge_bar()

func release_jump() -> bool:
	if is_airborne or not is_charging:
		return false
	var ratio: float = charge_ratio()
	var impulse: float = lerp(min_jump_impulse, max_jump_impulse, ratio)
	velocity = Vector2(impulse, -impulse * vertical_ratio)
	is_airborne = true
	jump_started_this_airborne = true
	is_charging = false
	charge_paused = false
	launch_stretch_timer = launch_stretch_duration
	_update_charge_bar()
	return true

func air_jump() -> bool:
	if not is_airborne:
		return false
	var impulse: float = max_jump_impulse * air_jump_strength_ratio
	velocity.x = max(velocity.x, impulse * 0.85)
	velocity.y = min(velocity.y, -impulse * vertical_ratio)
	launch_stretch_timer = launch_stretch_duration * 0.72
	return true

func update_motion(delta: float) -> void:
	if is_charging and not charge_paused:
		charge_time = min(charge_time + delta, max_charge_time)
	if is_airborne:
		velocity.y += gravity * delta
		var motion: Vector2 = velocity * delta
		var steps: int = 0
		while motion.length() > 0.001 and steps < MAX_COLLISION_ITERATIONS:
			var collision: KinematicCollision2D = move_and_collide(motion)
			if collision == null:
				break
			_apply_collision_response(collision.get_normal())
			motion = collision.get_remainder().slide(collision.get_normal())
			steps += 1
	if launch_stretch_timer > 0.0:
		launch_stretch_timer = max(0.0, launch_stretch_timer - delta)
	_update_charge_bar()
	_update_visual_feedback(delta)

func feet_y() -> float:
	return global_position.y + HALF_SIZE

func land_on(top_y: float) -> void:
	is_airborne = false
	jump_started_this_airborne = false
	is_charging = false
	charge_paused = false
	charge_time = 0.0
	launch_stretch_timer = 0.0
	velocity = Vector2.ZERO
	global_position.y = top_y - HALF_SIZE
	_update_charge_bar()

func reset_to_platform(platform: Platform) -> void:
	is_airborne = false
	jump_started_this_airborne = false
	is_charging = false
	charge_paused = false
	charge_time = 0.0
	launch_stretch_timer = 0.0
	velocity = Vector2.ZERO
	global_position = Vector2(platform.global_position.x, platform.top_y() - HALF_SIZE)
	_update_charge_bar()
	_update_visual_feedback(1.0)

func drop_from_platform() -> void:
	if is_airborne:
		return
	is_airborne = true
	jump_started_this_airborne = false
	is_charging = false
	charge_paused = false
	charge_time = 0.0
	velocity = Vector2(0.0, 40.0)
	_update_charge_bar()

func can_score_landing() -> bool:
	return jump_started_this_airborne

func _apply_collision_response(normal: Vector2) -> void:
	if abs(normal.x) > 0.65:
		velocity.x = -velocity.x * SIDE_BOUNCE_RATIO
		if abs(velocity.x) < 40.0:
			velocity.x = 0.0
	elif normal.y > 0.65:
		velocity.y = max(UNDERSIDE_PUSH_SPEED, abs(velocity.y) * 0.35)
	elif normal.y < -0.65 and velocity.y > 0.0:
		velocity.y = min(velocity.y, 36.0)

func charge_ratio() -> float:
	return clamp(charge_time / max_charge_time, 0.0, 1.0)

func _update_charge_bar() -> void:
	charge_bar.visible = not is_airborne and (always_show_charge_bar or is_charging)
	var fill_height: float = BAR_HEIGHT * charge_ratio()
	bar_fill.polygon = PackedVector2Array([
		Vector2(-BAR_WIDTH * 0.5, 0.0),
		Vector2(BAR_WIDTH * 0.5, 0.0),
		Vector2(BAR_WIDTH * 0.5, -fill_height),
		Vector2(-BAR_WIDTH * 0.5, -fill_height)
	])
	if is_charging and charge_ratio() >= MAX_CHARGE_FLASH_THRESHOLD:
		var phase: float = sin(Time.get_ticks_msec() * 0.018) * 0.5 + 0.5
		bar_fill.color = Color(0.58 + 0.25 * phase, 0.72 + 0.18 * phase, 0.54 + 0.18 * phase, 1.0)
	else:
		bar_fill.color = Color(0.443137, 0.67451, 0.490196, 1)

func _update_visual_feedback(delta: float) -> void:
	var target_scale: Vector2 = Vector2.ONE
	if is_charging and not is_airborne:
		var ratio: float = charge_ratio()
		target_scale = Vector2(1.0 + squash_strength * ratio, 1.0 - squash_strength * ratio)
	elif launch_stretch_timer > 0.0:
		var progress: float = 1.0 - launch_stretch_timer / launch_stretch_duration
		if progress < 0.38:
			var t1: float = progress / 0.38
			target_scale = Vector2(
				1.0 + launch_stretch_strength * t1,
				1.0 - launch_stretch_strength * 0.72 * t1
			)
		elif progress < 0.74:
			var t2: float = (progress - 0.38) / 0.36
			target_scale = Vector2(
				1.0 + launch_stretch_strength * (1.0 - t2) - launch_stretch_strength * 0.48 * t2,
				1.0 - launch_stretch_strength * 0.72 * (1.0 - t2) + launch_stretch_strength * 0.38 * t2
			)
		else:
			var t3: float = (progress - 0.74) / 0.26
			target_scale = Vector2(
				1.0 - launch_stretch_strength * 0.48 * (1.0 - t3),
				1.0 + launch_stretch_strength * 0.38 * (1.0 - t3)
			)
	visual.scale = visual.scale.lerp(target_scale, min(1.0, delta * squash_lerp_speed))
	var compensation_factor: float = 1.0 if (is_charging and not is_airborne) else squash_drop_factor
	var target_y_offset: float = (1.0 - target_scale.y) * HALF_SIZE * compensation_factor
	visual.position.y = lerp(visual.position.y, visual_base_position.y + target_y_offset, min(1.0, delta * squash_lerp_speed))
