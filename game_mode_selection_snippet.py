def choose_multiplayer_game_mode():
    """Choose between Luck Mode and Standard Mode for multiplayer"""
    screen = pygame.display.set_mode((700, 450))
    pygame.display.set_caption('Choose Multiplayer Mode')

    font_large = pygame.font.Font(None, 48)
    font_medium = pygame.font.Font(None, 24)
    font_small = pygame.font.Font(None, 18)

    luck_btn = Button(150, 200, 180, 60, "Luck Mode", font_size=28)
    standard_btn = Button(370, 200, 180, 60, "Standard Mode", font_size=24)
    back_btn = Button(250, 320, 200, 50, "Back", font_size=28)

    choice = None
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

            if luck_btn.handle_event(event):
                choice = "luck"
                running = False
            if standard_btn.handle_event(event):
                choice = "standard"
                running = False
            if back_btn.handle_event(event):
                choice = "back"
                running = False

        screen.fill(BG_COLOR)

        # Title
        title = font_large.render('Choose Game Mode', True, TEXT_COLOR)
        title_rect = title.get_rect(center=(350, 60))
        screen.blit(title, title_rect)

        # Luck Mode description
        luck_desc1 = font_small.render('Turn-based, one click per turn', True, TEXT_COLOR)
        luck_desc2 = font_small.render('No numbers shown, pure luck!', True, TEXT_COLOR)
        screen.blit(luck_desc1, (150, 270))
        screen.blit(luck_desc2, (150, 290))

        # Standard Mode description
        std_desc1 = font_small.render('Race mode - same board', True, TEXT_COLOR)
        std_desc2 = font_small.render('First to finish wins!', True, TEXT_COLOR)
        screen.blit(std_desc1, (370, 270))
        screen.blit(std_desc2, (370, 290))

        # Draw buttons
        luck_btn.draw(screen)
        standard_btn.draw(screen)
        back_btn.draw(screen)

        pygame.display.flip()

    return choice
