import sys
import pygame
from game import Game
from game.renderer import Renderer
from game.ui_manager import UIManager
from game.ui.menu import Menu, LoadGameMenu
from game.utils.save_load import SaveLoadSystem
from game import config


def main():
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    pygame.display.set_caption("Война Логистики - Пошаговый симулятор")
    clock = pygame.time.Clock()

    # Show main menu
    menu = Menu(screen)
    game = None
    renderer = None
    ui = None
    
    in_menu = True
    in_load_menu = False
    load_menu = None
    
    while in_menu:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if in_load_menu:
                result = load_menu.handle_event(event)
                if result == "back":
                    in_load_menu = False
                    load_menu = None
                elif result:
                    # Load the game
                    save_data = SaveLoadSystem.load_game(result)
                    if save_data:
                        game = Game(game_mode="ai")
                        SaveLoadSystem.restore_game(game, save_data)
                        renderer = Renderer(screen)
                        ui = UIManager(game)
                        game.ui = ui
                        in_menu = False
                        in_load_menu = False
            else:
                result = menu.handle_event(event)
                if result == "new_game_ai":
                    game = Game(game_mode="ai")
                    renderer = Renderer(screen)
                    ui = UIManager(game)
                    game.ui = ui
                    # Центрируем камеру на складе
                    wx, wy = game.map.player_warehouse
                    ts = renderer.tsize
                    view_w = config.SCREEN_WIDTH - config.PANEL_WIDTH
                    view_h = config.SCREEN_HEIGHT
                    renderer.camera_x = -(wx * ts - view_w // 2 + ts // 2)
                    renderer.camera_y = -(wy * ts - view_h // 2 + ts // 2)
                    in_menu = False
                elif result == "new_game_human":
                    game = Game(game_mode="hotseat")
                    renderer = Renderer(screen)
                    ui = UIManager(game)
                    game.ui = ui
                    # Центрируем камеру на складе
                    wx, wy = game.map.player_warehouse
                    ts = renderer.tsize
                    view_w = config.SCREEN_WIDTH - config.PANEL_WIDTH
                    view_h = config.SCREEN_HEIGHT
                    renderer.camera_x = -(wx * ts - view_w // 2 + ts // 2)
                    renderer.camera_y = -(wy * ts - view_h // 2 + ts // 2)
                    in_menu = False
                elif result == "load_game":
                    load_menu = LoadGameMenu(screen)
                    in_load_menu = True
                elif result == "quit":
                    pygame.quit()
                    sys.exit()
        
        if in_load_menu:
            load_menu.draw()
        else:
            menu.draw()
        
        clock.tick(60)

    # Main game loop
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            ui.handle_event(event, renderer)
            
            # Обработка сохранения/загрузки из ESP меню
            if hasattr(ui, 'esp_menu'):
                # Сохранение
                if ui.esp_menu.is_open and event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN and ui.esp_menu.current_tab == 2 and ui.esp_menu.selected_option == 0:
                        slot_name = f"save_turn_{game.turn}"
                        SaveLoadSystem.save_game(game, slot_name)
                        game.message = f"Игра сохранена: {slot_name}"
                        ui.esp_menu.is_open = False
                
                # Загрузка
                load_name = ui.esp_menu.handle_load()
                if load_name:
                    save_data = SaveLoadSystem.load_game(load_name)
                    if save_data:
                        game = Game(game_mode="ai")
                        SaveLoadSystem.restore_game(game, save_data)
                        renderer = Renderer(screen)
                        ui = UIManager(game)
                        game.ui = ui

        if game.game_over:
            renderer.render(game)
            _draw_game_over(screen, game)
            pygame.display.flip()
            clock.tick(30)
            for event in pygame.event.get():
                if event.type == pygame.QUIT or event.type == pygame.KEYDOWN:
                    running = False
            continue

        game.update()
        renderer.render(game)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


def _draw_game_over(screen, game):
    overlay = pygame.Surface((1280, 720), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    font = pygame.font.SysFont("consolas", 48)
    font2 = pygame.font.SysFont("consolas", 24)

    if game.victory:
        text = font.render("ПОБЕДА!", True, (50, 255, 50))
        sub = font2.render(game.message, True, (200, 255, 200))
    else:
        text = font.render("ПОРАЖЕНИЕ", True, (255, 50, 50))
        sub = font2.render(game.message, True, (255, 200, 200))

    tw = text.get_width()
    sw = sub.get_width()
    screen.blit(text, ((1280 - tw) // 2, 300))
    screen.blit(sub, ((1280 - sw) // 2, 360))

    exit_text = font2.render("Нажмите любую клавишу для выхода", True, (180, 180, 180))
    ew = exit_text.get_width()
    screen.blit(exit_text, ((1280 - ew) // 2, 420))


if __name__ == "__main__":
    main()
