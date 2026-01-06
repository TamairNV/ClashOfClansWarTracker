from jinja2 import Template

def test_render():
    # Mimic the data contexts
    # Case 1: War with None stats (Simulating the crash scenario)
    war_bad = {
        'total_stars': None,
        'avg_destruction': None,
        'total_attacks': None,
        'result': 'lose',
        # 'start_time' is usually datetime object but let's test string if needed or None
    }
    
    # Test destruction round
    # Original problematic code: {{ war.avg_destruction|round(1) }}
    tmpl_str = "{{ (war.avg_destruction or 0)|round(1) }}"
    t = Template(tmpl_str)
    print(f"Render dest: {t.render(war=war_bad)}")
    
    # Test result
    # {{ war.result|upper }}
    tmpl_str_res = "{{ war.result|upper }}"
    t2 = Template(tmpl_str_res)
    print(f"Render result: {t2.render(war=war_bad)}")
    
    # Test Win Loss
    win_loss = {'wins': None, 'losses': None, 'draws': None}
    tmpl_wl = "{{ (win_loss.wins or 0) }}"
    t3 = Template(tmpl_wl)
    print(f"Render WL: {t3.render(win_loss=win_loss)}")

    print("✅ Template snippet tests passed.")

if __name__ == "__main__":
    test_render()
