# **⚔️ Clan War Command Center**

A Flask-based war management system for Clash of Clans that uses probability algorithms to assign optimal targets and track player performance.

## **The Strategy Engine**

This app doesn't just list players; it solves the **Clan War Assignment Problem**.

### **1\. The Utility Function**

We calculate a **Win Probability (P3)** for every possible matchup based on:

* **TH Differential:** (+1 TH \= 95%, Equal \= 50%, \-1 TH \= 15%)  
* **Player Skill:** Derived from their Trust Score (Performance over last 10 wars).

### **2\. Strategic Protocols**

The engine automatically detects the war scenario:

* **Standard Protocol (Value Over Replacement):**  
  * Assigns the lowest-ranked player capable of 3-starring a base.  
  * Saves top attacks for cleanup or hard bases.  
  * Uses "Efficiency Penalty" to prevent a TH16 from dipping on a TH9 (wasted power).  
* **Mismatch Protocol ("The N-Shift"):**  
  * Triggered if enemies have significantly more Top THs than us.  
  * **Strategy:** Sacrifice bottom players to hit their \#1 and \#2 bases for safe 2-stars (Scout/Baby Drag).  
  * **Benefit:** Frees up our top players to crush their middle bases for guaranteed 3-stars.

### **3\. Confidence Meter**

The Green/Yellow/Red bar in the War Room represents the algorithm's confidence in a 3-star victory.

* **Green (\>80%):** "Dip" or "Easy Match".  
* **Yellow (50-80%):** "Equal Match".  
* **Red (\<50%):** "Reach" or "Scout".

## **🛠Setup & Installation**

### **1\. Prerequisites**

* Python 3.9+  
* MariaDB / MySQL  
* A Clash of Clans API Key (developer.clashofclans.com)

### **2\. Install Dependencies**

pip install flask pymysql coc.py asyncio cryptography

### **3\. Configuration**

Create a config.py file in the root directory:

class Config:  
    COC\_EMAIL \= "your-email"  
    COC\_PASSWORD \= "your-password"  
    CLAN\_TAG \= "\#YOURTAG"  
    DB\_HOST \= "localhost"  
    DB\_USER \= "root"  
    DB\_PASSWORD \= "password"  
    DB\_NAME \= "clash\_manager"

### **4\. Database Setup**

Run the SQL commands found in schema.sql (or just run the app, db\_manager handles most table creation dynamically).

## **The Automation Scripts (Cron Jobs)**

The app relies on background workers to fetch data. You must schedule these.

| Script | Frequency | Purpose |
| :---- | :---- | :---- |
| activity\_checker.py | Every 1 Hour | Tracks donations to find inactive players. |
| war\_tracker.py | Every 15 Mins | Updates the live war map and saves results. |
| performance\_tracker.py | End of War | Calculates Trust Scores and Ranks. |

**Example Linux Cron:**

\# Run war tracker every 15 mins  
\*/15 \* \* \* \* cd /path/to/app && /usr/bin/python3 war\_tracker.py \>\> logs/war.log 2\>&1

## **Project Structure**

* **app.py**: Main Flask application.  
* **routes.py**: Web logic (Roster & War Room views).  
* **war\_strategy.py**: The brain. Contains the matching algorithms.  
* **db\_manager.py**: Handles all SQL interactions.  
* **templates/**: HTML files (roster.html, war\_room.html).  
* **static/**: CSS and Images.