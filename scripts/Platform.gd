extends Node2D
class_name Platform

enum PlatformKind {
	NORMAL,
	NARROW,
	MOVING,
	FRAGILE
}

@export var width: float = 180.0:
	set(value):
		width = value
		if is_node_ready():
			_apply_shape()

@export var height: float = 28.0:
	set(value):
		height = value
		if is_node_ready():
			_apply_shape()

@export var platform_kind: PlatformKind = PlatformKind.NORMAL:
	set(value):
		platform_kind = value
		if is_node_ready():
			_apply_style()

@onready var visual: Polygon2D = $Visual
@onready var marker: Polygon2D = $Marker
@onready var collision_shape: CollisionShape2D = $StaticBody2D/CollisionShape2D

var base_x: float = 0.0
var move_amplitude: float = 0.0
var move_speed: float = 0.0
var move_phase: float = 0.0
var fragile_used: bool = false
var fragile_break_timer: float = -1.0

func _ready() -> void:
	base_x = global_position.x
	_apply_shape()
	_apply_style()

func _process(delta: float) -> void:
	if platform_kind == PlatformKind.MOVING and move_amplitude > 0.0:
		move_phase += delta * move_speed
		global_position.x = base_x + sin(move_phase) * move_amplitude

	if fragile_break_timer >= 0.0:
		fragile_break_timer -= delta
		if fragile_break_timer <= 0.0:
			queue_free()

func _apply_shape() -> void:
	if visual == null or collision_shape == null:
		return
	visual.polygon = PackedVector2Array([
		Vector2(-width * 0.5, -height * 0.5),
		Vector2(width * 0.5, -height * 0.5),
		Vector2(width * 0.5, height * 0.5),
		Vector2(-width * 0.5, height * 0.5)
	])
	var rect_shape: RectangleShape2D = collision_shape.shape as RectangleShape2D
	if rect_shape == null:
		rect_shape = RectangleShape2D.new()
		collision_shape.shape = rect_shape
	rect_shape.size = Vector2(width, height)

func _apply_style() -> void:
	if visual == null or marker == null:
		return
	if platform_kind == PlatformKind.NORMAL:
		visual.color = Color(0.403922, 0.603922, 0.45098, 1)
		marker.visible = false
	elif platform_kind == PlatformKind.NARROW:
		visual.color = Color(0.345098, 0.556863, 0.403922, 1)
		marker.visible = true
		marker.color = Color(0.90, 0.95, 0.86, 0.95)
		var inset: float = min(18.0, width * 0.22)
		marker.polygon = PackedVector2Array([
			Vector2(-width * 0.5 + inset, -height * 0.5 + 2.0),
			Vector2(width * 0.5 - inset, -height * 0.5 + 2.0),
			Vector2(width * 0.5 - inset, height * 0.5 - 2.0),
			Vector2(-width * 0.5 + inset, height * 0.5 - 2.0)
		])
	elif platform_kind == PlatformKind.MOVING:
		visual.color = Color(0.458824, 0.635294, 0.533333, 1)
		marker.visible = true
		marker.color = Color(0.95, 0.97, 0.90, 0.95)
		var arrow_half_h: float = height * 0.24
		var arrow_half_w: float = min(18.0, width * 0.2)
		marker.polygon = PackedVector2Array([
			Vector2(-arrow_half_w, -arrow_half_h),
			Vector2(0.0, -height * 0.34),
			Vector2(arrow_half_w, -arrow_half_h),
			Vector2(width * 0.18, 0.0),
			Vector2(arrow_half_w, arrow_half_h),
			Vector2(0.0, height * 0.34),
			Vector2(-arrow_half_w, arrow_half_h),
			Vector2(-width * 0.18, 0.0)
		])
	else:
		visual.color = Color(0.560784, 0.615686, 0.462745, 1)
		marker.visible = true
		marker.color = Color(0.94, 0.88, 0.78, 0.95)
		var crack_h: float = height * 0.45
		var crack_w: float = min(22.0, width * 0.27)
		marker.polygon = PackedVector2Array([
			Vector2(-crack_w, -crack_h),
			Vector2(-crack_w * 0.25, -crack_h * 0.35),
			Vector2(-crack_w * 0.6, 0.0),
			Vector2(crack_w * 0.15, crack_h * 0.15),
			Vector2(-crack_w * 0.2, crack_h),
			Vector2(crack_w * 0.75, crack_h * 0.05),
			Vector2(crack_w * 0.3, -crack_h * 0.2),
			Vector2(crack_w, -crack_h)
		])

func setup(kind: PlatformKind, configured_width: float, difficulty: float, generator: RandomNumberGenerator, motion_scale: float = 1.0) -> void:
	platform_kind = kind
	width = configured_width
	base_x = global_position.x
	fragile_used = false
	fragile_break_timer = -1.0
	move_phase = generator.randf_range(0.0, TAU)

	if platform_kind == PlatformKind.MOVING:
		move_amplitude = lerp(34.0, 72.0, difficulty) * motion_scale
		move_speed = lerp(1.35, 2.3, difficulty) * motion_scale
	else:
		move_amplitude = 0.0
		move_speed = 0.0

	_apply_shape()
	_apply_style()

func can_support_landing() -> bool:
	# Fragile platforms remain valid support during their break countdown.
	# They stop supporting only when removed from the scene.
	return true

func on_landed() -> void:
	if platform_kind == PlatformKind.FRAGILE and not fragile_used:
		fragile_used = true
		fragile_break_timer = 2.0
		visual.modulate = Color(1.0, 1.0, 1.0, 0.55)

func risk_bonus() -> int:
	if platform_kind == PlatformKind.NARROW:
		return 1
	if platform_kind == PlatformKind.MOVING:
		return 1
	if platform_kind == PlatformKind.FRAGILE:
		return 2
	return 0

func top_y() -> float:
	return global_position.y - height * 0.5

func support_overlap_width(world_x: float, half_extent: float, extra_margin: float = 0.0) -> float:
	var player_left: float = world_x - half_extent
	var player_right: float = world_x + half_extent
	var platform_left: float = global_position.x - width * 0.5 - extra_margin
	var platform_right: float = global_position.x + width * 0.5 + extra_margin
	return max(0.0, min(player_right, platform_right) - max(player_left, platform_left))

func left_edge(extra_margin: float = 0.0) -> float:
	return global_position.x - width * 0.5 - extra_margin

func right_edge(extra_margin: float = 0.0) -> float:
	return global_position.x + width * 0.5 + extra_margin
