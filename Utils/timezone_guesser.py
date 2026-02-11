
from datetime import datetime
import statistics
from collections import Counter

class TimezoneGuesser:
    def __init__(self):

        self.offset_map = {
            -8: "USA/Canada (PST)",
            -7: "USA (MST)",
            -6: "USA (CST)",
            -5: "USA/Canada (EST)",
            -4: "Canada (AST) / Caribbean",
            -3: "South America (Brazil/Arg)",
            0: "UK / Portugal / Ireland",
            1: "Europe (CET)",
            2: "Europe (EET) / South Africa",
            3: "Middle East / Russia (Moscow)",
            4: "UAE / Mauritius",
            5: "Pakistan / Maldives",
            5.5: "India",
            6: "Bangladesh",
            7: "SE Asia (Vietnam/Thailand)",
            8: "China / Singapore / Philippines",
            9: "Japan / Korea",
            10: "Australia (AEST)",
            11: "Australia (AEDT)",
            12: "New Zealand"
        }

    def guess_timezone(self, timestamps):

        if not timestamps or len(timestamps) < 5:
            return None, None, 0.0, None

        # 1. Extract Hours (0-23)
        hours = []
        for ts in timestamps:
            if isinstance(ts, str):
                try:
                    ts = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
                except:
                    continue
            if isinstance(ts, datetime):
                hours.append(ts.hour)
        
        if not hours:
            return None, None, 0.0, None

        best_window_start = 0
        max_events = 0
        
        # Check every start hour 0-23
        for start_h in range(24):
            count = 0
            for h in hours:
                # Check if hour is in window [start, start+4] handling wrap-around
                diff = (h - start_h) % 24
                if diff < 6: # 6 hour window
                    count += 1
            
            if count > max_events:
                max_events = count
                best_window_start = start_h
                

        peak_utc = (best_window_start + 3) % 24
        

        
        raw_offset = 21 - peak_utc
        
        # Normalize to [-12, +12]
        if raw_offset > 12:
            raw_offset -= 24
        elif raw_offset < -12:
            raw_offset += 24
            
        # 4. Map to Country
        closest_offset = min(self.offset_map.keys(), key=lambda x: abs(x - raw_offset))
        
        # Handle India (5.5) special case if raw is close to 5 or 6
        if 5 <= raw_offset <= 6:
            # Check if we can refine? For now just snap to closest int or 5.5
            if abs(raw_offset - 5.5) < 0.5:
                closest_offset = 5.5
        
        country = self.offset_map.get(closest_offset, "Unknown")
        timezone_str = f"UTC{'+' if closest_offset >= 0 else ''}{closest_offset}"
        
        # 5. Calculate Confidence
        # Factors: Sample Size, Concentration
        sample_size_score = min(1.0, len(hours) / 20.0) # Max confidence at 20 events
        concentration_score = max_events / len(hours) # % of events in the peak window
        
        confidence = (sample_size_score * 0.4) + (concentration_score * 0.6)

        
        start_utc = int((peak_utc - 2) % 24)
        end_utc = int((peak_utc + 2) % 24)
        
        # Format: "14:00 - 18:00 UTC"
        time_label = f"{start_utc:02d}:00 - {end_utc:02d}:00 UTC"
        
        return timezone_str, country, round(confidence * 100, 1), time_label



