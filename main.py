# spec2test/main.py

from flow import spec2test_flow
from tui import console, print_header, print_success
import sys
# --- START OF FIX ---
import asyncio
import os # Import os for path manipulation
# --- END OF FIX ---

# --- START OF FIX ---
# Make the main function asynchronous
async def main():
# --- END OF FIX ---
    """
    Main function to run the Spec2Test AI-powered verification copilot.
    """
    print_header()
    
    shared = {
        "debug_attempt_count": 0 # Initialize debug counter
    }
    
    try:
        # --- START OF FIX ---
        # Await the async execution of the flow
        await spec2test_flow.run_async(shared)
        # --- END OF FIX ---
        
        console.print()
        if shared.get("output_file_paths"):
            final_message = "All files have been generated successfully!"
            if shared.get('simulation_script_status'):
                 final_message += f"\n- {shared['simulation_script_status']}"
            print_success(final_message)
            
            output_dir = os.path.dirname(shared["output_file_paths"][0])
            console.print("\n[info]To run the simulation, navigate to the output directory and execute the script:[/info]")
            console.print(f"  [prompt]cd {output_dir} && ./run_sim.sh[/prompt]")
        else:
            console.print("[warning]Flow completed, but no files were written (likely aborted by user).[/warning]")

    except Exception as e:
        console.print("\n[danger]An unexpected error occurred and the flow was terminated.[/danger]")
        console.print_exception(show_locals=True)
        sys.exit(1)

if __name__ == "__main__":
    # --- START OF FIX ---
    # Run the async main function
    asyncio.run(main())
    # --- END OF FIX ---