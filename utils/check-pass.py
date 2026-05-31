import getpass
import math

from zxcvbn import zxcvbn

# Display the header
print("\n--- PASSPHRASE STRENGTH CHECK ---")

# Securely read the passphrase
passphrase = getpass.getpass("Enter your LUKS passphrase: ")

if not passphrase:
    print("Error: Input is empty.")
    exit()

# Perform the strength analysis
results = zxcvbn(passphrase)

# DEBUG: Print raw results to verify calculations
# print(f"\nDEBUG: {results}")

# Calculate entropy using log2 of guesses
# This is the most accurate representation of the search space complexity
guesses = float(results.get("guesses", 1))
entropy_calc = math.log2(guesses)

# Extract other metrics
crack_times = results.get("crack_times_display", {})
crack_time = crack_times.get("offline_slow_hashing_1e4_per_second", "N/A")
score = results.get("score", 0)

# Extract feedback
feedback_data = results.get("feedback") or {}
suggestions = feedback_data.get("suggestions", ["No specific suggestions."])
warning = feedback_data.get("warning", "")

# Output the results
print("\n[ Analysis Results ]")
print(f"Time to crack (estimated): {crack_time}")
print(f"Entropy: {entropy_calc:.2f} bits (log2(guesses))")
print(f"zxcvbn Score (0-4): {score}")

if warning:
    print(f"Warning: {warning}")

# Evaluation logic
if score < 4:
    print("\n🔑 **Recommendation: Increase Passphrase Strength**")
    print("Suggestions: ", ", ".join(suggestions))
else:
    print("\n✅ **Passphrase is Strong for Long-Term LUKS Security**")

print("---------------------------------\n")
