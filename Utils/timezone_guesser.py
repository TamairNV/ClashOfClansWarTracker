
from datetime import datetime
import statistics
from collections import Counter

class TimezoneGuesser:
    def __init__(self):
        # Mapping of UTC offsets to likely countries/regions
        # This is a heuristic and can be expanded
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
        """
        Analyzes a list of UTC timestamps to guess the player's timezone.
        Returns: (timezone_str, country_guess, confidence_score)
        """
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

        # 2. Find Peak Activity Hour (UTC)
        # We use a circular mean or just the mode/median of the "active window"
        # Simple approach: Find the 4-hour window with the most events
        
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
                
        # Peak is roughly in the middle of the window
        peak_utc = (best_window_start + 3) % 24
        
        # 3. Infer Offset
        # Assumption: Peak gaming time is 21:00 (9 PM) local time
        # Offset = Local - UTC
        # Offset = 21 - Peak_UTC
        
        raw_offset = 21 - peak_utc
        
        # Normalize to [-12, +12]
        if raw_offset > 12:
            raw_offset -= 24
        elif raw_offset < -12:
            raw_offset += 24
            
        # 4. Map to Country
        # Find closest key in offset_map
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
        
        # 6. Format Favorite Time Label (UTC)
        # User requested actual online time, not a local guess.
        # peak_utc is the center of the 4-hour window.
        
        start_utc = int((peak_utc - 2) % 24)
        end_utc = int((peak_utc + 2) % 24)
        
        # Format: "14:00 - 18:00 UTC"
        time_label = f"{start_utc:02d}:00 - {end_utc:02d}:00 UTC"
        
        return timezone_str, country, round(confidence * 100, 1), time_label

if __name__ == "__main__":
    # Test
    guesser = TimezoneGuesser()
    
    # Simulate India (UTC+5.5). Peak 9PM Local = 3:30 PM UTC (15.5)
    # Let's say events around 13:00 - 18:00 UTC
    test_data_india = [
        datetime(2023, 1, 1, 14, 0, 0),
        datetime(2023, 1, 1, 15, 30, 0),
        datetime(2023, 1, 1, 16, 0, 0),
        datetime(2023, 1, 1, 13, 0, 0),
        datetime(2023, 1, 1, 17, 0, 0),
        datetime(2023, 1, 1, 15, 0, 0),
    ]
    print(f"India Test: {guesser.guess_timezone(test_data_india)}")
    
    # Simulate NY (UTC-5). Peak 9PM Local = 2AM UTC next day (02:00)
    # Events around 00:00 - 05:00 UTC
    test_data_ny = [
        datetime(2023, 1, 1, 1, 0, 0),
        datetime(2023, 1, 1, 2, 0, 0),
        datetime(2023, 1, 1, 3, 0, 0),
        datetime(2023, 1, 1, 0, 0, 0),
        datetime(2023, 1, 1, 4, 0, 0),
    ]
    print(f"NY Test: {guesser.guess_timezone(test_data_ny)}")
