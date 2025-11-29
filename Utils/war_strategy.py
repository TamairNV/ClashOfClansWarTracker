def calculate_hit_probability(attacker, defender):
    """
    Calculates P(3*) based on TH differential and Player Trust Score.
    Research Table 2 Implementation.
    """
    delta_th = attacker['th'] - defender['town_hall_level']
    trust_multiplier = attacker.get('score', 50) / 50.0  # 1.0 is average skill

    # Baseline P(3*) from Research
    if delta_th >= 2:
        base_prob = 0.99  # Bully
    elif delta_th == 1:
        base_prob = 0.95  # Dip
    elif delta_th == 0:
        base_prob = 0.50  # Peer (Root Rider Meta)
    elif delta_th == -1:
        base_prob = 0.15  # Reach
    else:
        base_prob = 0.02  # Suicide

    # Adjust for skill (Cap at 95%, floor at 1%)
    final_prob = base_prob * trust_multiplier
    return min(0.95, max(0.01, final_prob))


def detect_mismatch(our_team, enemy_team):
    """
    Protocol A: The 'Mismatch' Protocol.
    Checks if enemy has significantly more Top-Tier THs.
    """
    # Count TH16s (or whatever is max)
    our_max = sum(1 for p in our_team if p['th'] >= 16)
    their_max = sum(1 for p in enemy_team if p['town_hall_level'] >= 16)

    # If they have 3+ more Max THs, trigger Shift
    if their_max > our_max + 2:
        return True, their_max - our_max
    return False, 0


def get_war_recommendations(our_team, enemy_team, war_context=None):
    recommendations = []
    
    # Default context if None
    if not war_context:
        war_context = {'hours_left': 24, 'score_diff': 0}

    hours_left = war_context.get('hours_left', 24)
    
    # "Secure the Win" Mode:
    # If < 4 hours left, we prioritize cleaning up lower bases over risking top bases.
    secure_win_mode = hours_left <= 4

    # Sort lists
    our_team_sorted = sorted(our_team, key=lambda x: (x['th'], x['score']), reverse=True)
    enemy_team_sorted = sorted(enemy_team, key=lambda x: x['map_position'])

    # Detect Protocol
    is_mismatch, shift_n = detect_mismatch(our_team_sorted, enemy_team_sorted)

    # Track assigned targets to prevent double-booking (simple greedy approach)
    assigned_targets = set()

    for i, player in enumerate(our_team_sorted):
        rec = {
            'player': player,
            'target': None,
            'reason': "Hold for cleanup",
            'confidence': 0
        }

        if player['attacks_used'] >= 2:
            rec['reason'] = "✅ Done"
            recommendations.append(rec)
            continue

        # --- STRATEGY ENGINE ---

        best_target = None
        best_score = -1
        strategy_type = ""

        # 1. MISMATCH PROTOCOL (The "Mirror Plus")
        # If we are outmatched, bottom players hit TOP bases for safe 2-stars.
        if is_mismatch and i >= (len(our_team_sorted) - shift_n):
            # This is a sacrificial lamb (Bottom player)
            # Find a top base not yet 2-starred
            for enemy in enemy_team_sorted[:shift_n]:  # Look at top N enemies
                if enemy['opponent_tag'] in assigned_targets: continue # Skip if already assigned
                
                if enemy['stars'] < 2:
                    best_target = enemy
                    strategy_type = "🛡️ SCOUT/2★ (Mismatch Strat)"
                    rec['confidence'] = 85  # High confidence in 2-star
                    break

        # 2. STANDARD PROTOCOL (Bottom-Up Wave)
        if not best_target:
            # Search for the highest Value Over Replacement
            # We prefer: High % Chance of 3-Star on a base that isn't cleared.

            potential_targets = []

            for enemy in enemy_team_sorted:
                if enemy['stars'] == 3: continue  # Skip cleared
                if enemy['opponent_tag'] in assigned_targets: continue # Skip if already assigned

                prob = calculate_hit_probability(player, enemy)

                # Scoring Heuristic:
                # Value = Probability * (Stars to Gain)
                stars_to_gain = 3 - enemy['stars']
                expected_value = prob * stars_to_gain
                
                # --- SECURE THE WIN LOGIC ---
                if secure_win_mode:
                    # If target is already 2-starred, heavily penalize unless it's a guaranteed 3-star
                    if enemy['stars'] == 2:
                        expected_value *= 0.2 # Massive penalty for hitting 2-star bases
                        
                    # If target is low (Dip) and not cleared, boost it to ensure cleanup
                    # We want top players to dip and clear lower bases
                    if prob > 0.9:
                        expected_value *= 2.0 # Prioritize guaranteed stars

                # Penalty for "Dipping Too Deep" (Wasting a TH16 on a TH12)
                # In Secure Win Mode, we relax this penalty because stars matter more than efficiency
                th_waste = max(0, player['th'] - enemy['town_hall_level'] - 1)
                efficiency_penalty = th_waste * 0.2
                
                if secure_win_mode:
                    efficiency_penalty *= 0.5 # Lower penalty late in war

                final_score = expected_value - efficiency_penalty

                potential_targets.append((final_score, prob, enemy))

            # Pick best
            potential_targets.sort(key=lambda x: x[0], reverse=True)

            if potential_targets:
                score, prob, target = potential_targets[0]
                best_target = target
                rec['confidence'] = int(prob * 100)

                if prob > 0.8:
                    strategy_type = "🎯 DIP (Guaranteed 3★)"
                elif prob > 0.5:
                    strategy_type = "⚔️ ATTACK (Good Match)"
                else:
                    strategy_type = "⚠️ REACH (High Risk)"
                    
                if secure_win_mode and target['stars'] < 3 and prob > 0.9:
                     strategy_type = "🧹 CLEANUP (Secure Win)"

        # Assign
        if best_target:
            rec['target'] = best_target
            rec['reason'] = strategy_type
            assigned_targets.add(best_target['opponent_tag'])

        recommendations.append(rec)

    return recommendations