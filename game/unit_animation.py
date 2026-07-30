class UnitAnimation:
    """Movement animation system."""

    def __init__(self, game):
        self.game = game

    def start_unit_animation(self, unit, path, callback=None):
        if not path:
            if callback:
                callback()
            return
        g = self.game
        g._anim_active = True
        g._anim_unit = unit
        g._anim_path = path
        g._anim_step = 0
        g._anim_timer = 2
        g._anim_callback = callback
        unit._anim_x = unit.x
        unit._anim_y = unit.y

    def queue_movement_animation(self, unit, path, callback=None):
        self.game._anim_queue.append((unit, path, callback))

    def update_movement_animation(self):
        g = self.game
        if not g._anim_active:
            if g._anim_queue:
                unit, path, callback = g._anim_queue.pop(0)
                self.start_unit_animation(unit, path, callback)
            return
        g._anim_timer -= 1
        if g._anim_timer > 0:
            return
        if g._anim_step < len(g._anim_path):
            nx, ny = g._anim_path[g._anim_step]
            unit = g._anim_unit
            unit._anim_x = nx
            unit._anim_y = ny
            g.map.remove_unit(unit)
            unit.x, unit.y = nx, ny
            g.map.add_unit(unit, nx, ny)
            g._anim_step += 1
            g._anim_timer = g._anim_delay
            g.message = f"{unit.name} идёт... ({g._anim_step}/{len(g._anim_path)})"
        else:
            unit = g._anim_unit
            if hasattr(unit, '_anim_x'):
                del unit._anim_x
            if hasattr(unit, '_anim_y'):
                del unit._anim_y
            unit.moved = True
            g._anim_active = False
            g._anim_unit = None
            g._anim_path = []
            g._anim_step = 0
            if g._anim_callback:
                g._anim_callback()
                g._anim_callback = None

    def is_animating(self):
        g = self.game
        return g._anim_active or len(g._anim_queue) > 0
