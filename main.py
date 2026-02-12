import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path

# --- Configuration ---
# Ensure the database file path is project-relative
DB_PATH = str(Path(__file__).resolve().parents[0] / 'data' / 'arbitrage.db')
BASE_DIR = Path(__file__).resolve().parents[0]

def run_script(script_name, args=None):
    """Run a Python script (located in the same directory as this file) and return success status"""
    try:
        script_path = str(BASE_DIR / script_name)
        print(f'Running {script_path}...')
        # Using sys.executable ensures we use the current .venv python
        command = [sys.executable, script_path]
        if args:
            command.extend(args)
        result = subprocess.run(
            command,
            capture_output=True, 
            text=True, 
            timeout=300
        )
        
        if result.returncode == 0:
            print(f'{script_name} completed successfully.')
            return True
        else:
            print(f'{script_name} failed (Code {result.returncode})')
            if result.stderr:
                print(f'   Error: {result.stderr.strip()}')
            return False
            
    except subprocess.TimeoutExpired:
        print(f'{script_name} timed out after 5 minutes.')
        return False
    except Exception as e:
        print(f'Unexpected error running {script_name}: {e}')
        return False

def main():
    """Main orchestrator for the laptop arbitrage scraper"""
    start_time = datetime.now()
    results = {}

    print('='*45)
    print('   LAPTOP ARBITRAGE & PRICING SCRAPER   ')
    print(f'   Started: {start_time.strftime("%Y-%m-%d %H:%M:%S")}')
    print('='*45)

    # Define the execution pipeline
    pipeline = [
        ('Database Setup', 'db_setup.py', True, None),      # (Label, Script, Exit on fail, Args)
        ('Component Scraper', 'scraper_components.py', False, None),
        ('Laptop Scraper', 'scraper_laptops.py', False, ['--mode', 'live']),
        ('Analysis/Reporting', 'analyzer.py', False, None)
    ]

    for label, script, critical, args in pipeline:
        print(f'\n--- Phase: {label} ---')
        
        # Check if script exists before trying to run it
        if not os.path.exists(script):
            print(f'File not found: {script}')
            results[label] = 'MISSING'
            if critical: break
            continue

        success = run_script(script, args)
        results[label] = 'SUCCESS' if success else 'FAILED'
        
        if not success and critical:
            print(f'\nCritical failure in {label}. Aborting pipeline.')
            break

    # --- Final Summary ---
    end_time = datetime.now()
    duration = end_time - start_time
    
    print('\n' + '='*45)
    print(f'EXECUTION SUMMARY')
    print(f'Total Duration: {duration}')
    for step, status in results.items():
        icon = '[+]' if status == 'SUCCESS' else '[-]' if status == 'FAILED' else '[!]'
        print(f'{icon} {step.ljust(20)}: {status}')
    print('='*45)

if __name__ == '__main__':
    main()