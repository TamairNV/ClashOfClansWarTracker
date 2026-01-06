import sys
import os
import datetime
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config
from Utils.sqlManager import SQLManager
# from jinja3 import Template # No need for full jinja2 yet if python logic crashes first

def simulate_route():
    print("🚀 Simulating /stats route...")
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
    
    try:
        # 1. War History & Trend
        print("Fetching history...")
        history = db.get_clan_war_history_stats(limit=20)
        print(f"Fetched {len(history)} wars.")
        
        # Process for Trend Chart
        trend_dates = []
        trend_stars = []
        trend_dest = []
        
        for i, war in enumerate(reversed(history)):
            print(f"Processing War {i} (ID: {war.get('war_id')})...")
            
            # Check Start Time
            st = war.get('start_time')
            if not isinstance(st, datetime.datetime):
                print(f"❌ Error: Start time is {type(st)}: {st}")
            
            trend_dates.append(st.strftime('%m-%d'))
            
            # Use Avg Stars (rounded)
            # Logic from routes.py: val = war['avg_stars'] or 0
            raw_avg = war.get('avg_stars')
            val = raw_avg or 0
            print(f"   Avg Stars Raw: {raw_avg} ({type(raw_avg)}) -> Val: {val}")
            
            trend_stars.append(round(val, 2))
            
            raw_dest = war.get('avg_destruction')
            dest = raw_dest or 0
            print(f"   Avg Dest Raw: {raw_dest} ({type(raw_dest)}) -> Dest: {dest}")
            trend_dest.append(dest)
            
        print("✅ Trend processing complete.")
        
        # 2. Activity Clock
        print("Fetching activity...")
        activity_data = db.get_clan_activity_distribution()
        print("✅ Activity fetch complete.")
        
        # 3. Win/Loss Ratio
        print("Fetching Win/Loss...")
        win_loss = db.get_clan_win_loss_ratio(limit=50)
        print(f"✅ Win/Loss fetch complete: {win_loss}")
        
        # If we got here, Python logic is fine.
        # Check template rendering (mock)
        print("🎨 Simulating Template Render (basic check)...")
        from jinja2 import Template
        
        # Mimic the problematic parts of clan_stats.html
        # Note: we need to pass the PROCESSED lists (trend_dates etc)
        
        # Snippet from template:
        # data: {{ trend_stars | tojson }},
        # <td>{{ (war.total_stars or 0) }} ★</td>
        # <td>{{ (war.avg_destruction or 0)|round(1) }}%</td>
        
        # Only check history table loop since correct context is passed
        tmpl = """
        {% for war in history %}
            Result: {{ war.result|upper }}
            Stars: {{ (war.total_stars or 0) }}
            Dest: {{ (war.avg_destruction or 0)|round(1) }}
        {% endfor %}
        """
        t = Template(tmpl)
        out = t.render(history=history)
        print("✅ Template Render check passed.")
        
    except Exception as e:
        print(f"❌ CRASH DETECTED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    simulate_route()
