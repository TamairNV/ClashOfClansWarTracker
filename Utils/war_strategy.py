def calculate_pow(player):
    """
    Player Offensive Weight (POW) Index.
    POW = Town Hall Level + (Trust Score / 100)
    """
    th = player.get('th', 0)
    trust = player.get('score', 50)
    return th + (trust / 100.0)

def calculate_tds(target, total_targets):
    """
    Target Difficulty Score (TDS) Index.
    TDS = Town Hall Level + (1 - MapRank/MapSize)
    """
    th = target.get('town_hall_level', 0)
    rank = target.get('map_position', 1)
    # Normalize rank impact (0 to 1)
    rank_factor = 1.0 - (rank / max(1, total_targets))
    return th + rank_factor

def strategy_cw(our_team, enemy_team, war_context):
    """
    Standard Clan War (CW) Algorithm.
    Goal: Absolute Star Maximization (3-Stars).
    """
    recommendations = []
    assigned_targets = set()
    
    # Calculate and store metrics for display
    for p in our_team:
        p['pow'] = calculate_pow(p)
        
    for e in enemy_team:
        e['tds'] = calculate_tds(e, len(enemy_team))

    # Sort by POW and TDS
    our_team_sorted = sorted(our_team, key=lambda x: x['pow'], reverse=True)
    enemy_team_sorted = sorted(enemy_team, key=lambda x: x['tds'], reverse=True)
    
    # Phase 1: Initialization (Bottom 25% Enemies -> Lowest POW Players)
    # Only applies if attacks haven't started (fresh war)
    # But for simplicity, we apply this logic generally for fresh hits.
    
    # Phase 2: Dynamic Cleanup/Pinch
    # Prioritize 1-star bases, then low % 2-star bases.
    
    # We will use a greedy approach based on Marginal Star Gain.
    
    for player in our_team_sorted:
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
            
        best_target = None
        best_score = -1
        strategy_type = ""
        
        # Search for best target
        for enemy in enemy_team_sorted:
            if enemy['opponent_tag'] in assigned_targets: continue
            if enemy['stars'] == 3: continue # Skip cleared
            
            # Calculate Probability (using existing logic or simplified)
            # We reuse the existing probability logic but adapted
            prob = calculate_hit_probability(player, enemy)
            
            stars_to_gain = 3 - enemy['stars']
            expected_value = prob * stars_to_gain
            
            # Heuristics from Research
            
            # 1. Cleanup Priority
            if enemy['stars'] == 1:
                expected_value *= 1.5 # Boost 1-star cleanup
            
            # 2. Pinch/Scout Logic
            # If high TDS and unattacked, and player is low POW -> Scout?
            # For now, we focus on maximizing EV.
            
            # 3. Time Fail / Meta Army (Not implemented yet as we lack army data)
            
            if expected_value > best_score:
                best_score = expected_value
                best_target = enemy
                rec['confidence'] = int(prob * 100)
                
                if prob > 0.9:
                    strategy_type = "🧹 CLEANUP"
                elif prob > 0.6:
                    strategy_type = "⚔️ ATTACK"
                else:
                    strategy_type = "⚠️ REACH"

        if best_target:
            rec['target'] = best_target
            rec['reason'] = strategy_type
            assigned_targets.add(best_target['opponent_tag'])
            
        recommendations.append(rec)
        
    return recommendations

def strategy_cwl(our_team, enemy_team, war_context):
    """
    Clan War League (CWL) Algorithm.
    Goal: Maximize Medals (2-Star Assurance + Dip 3-Stars).
    """
    recommendations = []
    assigned_targets = set()
    
    # Calculate and store metrics for display
    for p in our_team:
        p['pow'] = calculate_pow(p)
        
    for e in enemy_team:
        e['tds'] = calculate_tds(e, len(enemy_team))
        
    # Sort by POW and TDS
    our_team_sorted = sorted(our_team, key=lambda x: x['pow'], reverse=True)
    enemy_team_sorted = sorted(enemy_team, key=lambda x: x['tds'], reverse=True)
    
    # We need to assign EVERYONE (1 attack each).
    # Iterate through enemies from High TDS down.
    
    # Create a pool of available players
    available_players = [p for p in our_team_sorted if p['attacks_used'] == 0]
    # Sort available players by POW (High to Low)
    available_players.sort(key=calculate_pow, reverse=True)
    
    # We will assign targets to players.
    # But the algorithm says "Iterate through Enemy Roster".
    
    # Mapping: Target -> Player
    assignments = {}
    
    # 1. Mismatch / Safe 2-Star Logic
    # For High TDS bases (Target TH >= Player TH + 2)
    # We want the LOWEST POW player who can get 2 stars.
    
    # 2. Mid-Range (Peer)
    # Assign High POW for secure 2-star.
    
    # 3. Dip (3-Star Guarantee)
    # Assign High POW to Low targets.
    
    # Let's try a simplified pass:
    # We want to maximize total stars/medals.
    
    # Pass 1: Secure 3-Stars (Dips)
    # Assign Highest POW players to targets they can 3-star (TH - 1)
    # But wait, the prompt says "Strategic Dip" comes AFTER "Initial Assignment".
    
    # Let's follow the prompt's order:
    # "Iterate through the Enemy_Roster from high TDS (Target Rank 1) down."
    
    for enemy in enemy_team_sorted:
        if enemy['opponent_tag'] in assigned_targets: continue
        if enemy['stars'] == 3: continue # Skip cleared
        if not available_players: break
        
        target_th = enemy['town_hall_level']
        assigned_player = None
        reason = ""
        
        # a. Mismatch (Target TH >= P_TH + 2) -> Lowest POW with >85% 2-star prob
        # We don't have a specific 2-star prob calculator, but we can proxy.
        # Proxy: If P_TH >= Target_TH - 2, maybe?
        # Actually, a TH12 can 2-star a TH16 with Blimp.
        # So almost anyone can 2-star if skilled.
        # We'll look for the Lowest POW player.
        
        # Find candidates for this target
        candidates = []
        for p in available_players:
            p_th = p['th']
            pow_score = calculate_pow(p)
            
            # Calculate 2-star prob (Proxy)
            # Base 2-star is easier.
            prob_2star = 0.90 # Assume high base
            if target_th > p_th:
                prob_2star -= (target_th - p_th) * 0.10
            
            # HRI Check (Trust Score)
            if p.get('score', 50) < 70:
                prob_2star -= 0.20
                
            candidates.append((p, prob_2star, pow_score))
            
        # Sort candidates
        # We want: High Prob, Low POW
        candidates.sort(key=lambda x: (x[1] > 0.85, -x[2])) # True (High Prob) first, then Low POW (negative sort?)
        # Wait, sorted(reverse=True) puts True first.
        # Then we want Lowest POW. So we want smallest POW to be first?
        # No, if we reverse=True:
        # (True, -POW) -> True comes before False.
        # For POW: -5 vs -10. -5 is bigger. So -5 comes first.
        # We want Lowest POW. So we want -POW to be LARGEST (closest to 0).
        # So High POW = 100. Low POW = 50.
        # -100 vs -50. -50 is bigger.
        # So reverse=True puts Low POW first. Correct.
        
        candidates.sort(key=lambda x: (x[1] > 0.85, -x[2]), reverse=True)
        
        if candidates:
            best_candidate = candidates[0] # Best fit
            p, prob, pow_s = best_candidate
            
            if prob > 0.85:
                # Good match
                assigned_player = p
                reason = "🛡️ SAFE 2★"
                if p['th'] >= target_th:
                     reason = "⚔️ PEER HIT"
                if p['th'] > target_th:
                    reason = "🎯 DIP 3★"
            else:
                # If we can't find a safe 2-star, maybe we skip this hard base for now?
                # Or we burn a high POW?
                # For now, take the best we have.
                assigned_player = p
                reason = "⚠️ BEST EFFORT"

        if assigned_player:
            assignments[assigned_player['player_tag']] = (enemy, reason)
            assigned_targets.add(enemy['opponent_tag'])
            available_players.remove(assigned_player)

    # Compile recommendations
    for player in our_team:
        rec = {
            'player': player,
            'target': None,
            'reason': "Reserve",
            'confidence': 0
        }
        
        if player['attacks_used'] >= 1:
            rec['reason'] = "✅ Done"
            recommendations.append(rec)
            continue
            
        if player['player_tag'] in assignments:
            target, reason = assignments[player['player_tag']]
            rec['target'] = target
            rec['reason'] = reason
            # Recalculate confidence for display
            rec['confidence'] = int(calculate_hit_probability(player, target) * 100)
            
        recommendations.append(rec)
        
    return recommendations

def calculate_hit_probability(attacker, defender):
    """
    Calculates P(3*) based on TH differential and Player Trust Score.
    Research Table 2 Implementation.
    """
    delta_th = attacker['th'] - defender['town_hall_level']
    
    # Baseline P(3*) from Research (Conservative Update)
    if delta_th >= 2:
        base_prob = 0.99  # Bully (TH16 vs TH14)
    elif delta_th == 1:
        base_prob = 0.90  # Dip (TH16 vs TH15)
    elif delta_th == 0:
        base_prob = 0.40  # Peer (TH16 vs TH16)
    elif delta_th == -1:
        base_prob = 0.10  # Reach (TH15 vs TH16)
    else:
        base_prob = 0.01  # Suicide

    # --- Map Rank Penalty ---
    attacker_rank = attacker.get('map_position', 999)
    defender_rank = defender.get('map_position', 999)
    
    rank_diff = defender_rank - attacker_rank 
    
    if rank_diff < 0:
        rank_penalty = abs(rank_diff) * 0.05 
        base_prob -= rank_penalty
    elif rank_diff > 0:
        rank_bonus = min(0.20, rank_diff * 0.02) 
        base_prob += rank_bonus

    # Adjust for skill (Triple Rate)
    # Default to 0.30 if missing or 0 (new player)
    triple_rate = attacker.get('triple_rate', 0.30)
    if triple_rate == 0: triple_rate = 0.30
    
    skill_factor = triple_rate - 0.30
    skill_factor = max(-0.25, min(0.40, skill_factor))
    
    final_prob = base_prob + skill_factor
    
    # Ensure reasonable bounds (e.g. never below 5% for a peer hit)
    min_prob = 0.05
    if delta_th >= 0: min_prob = 0.20
    
    return min(0.95, max(min_prob, final_prob))

def get_war_recommendations(our_team, enemy_team, war_context=None):
    if not war_context:
        war_context = {'hours_left': 24, 'score_diff': 0, 'war_type': 'regular'}
        
    # Assign map_position to our_team (assuming they are not sorted or missing it)
    # Map order is usually TH desc, then Score/Trophies desc.
    # We'll sort them and assign 1..N
    our_team_sorted_for_rank = sorted(our_team, key=lambda x: (x['th'], x['score']), reverse=True)
    for i, p in enumerate(our_team_sorted_for_rank):
        p['map_position'] = i + 1
        
    war_type = war_context.get('war_type', 'regular').lower()
    
    if war_type == 'cwl':
        return strategy_cwl(our_team, enemy_team, war_context)
    else:
        return strategy_cw(our_team, enemy_team, war_context)