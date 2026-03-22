from chaos import ChaosEngine

def main():
    # Toggle between "gemini" or "openai"
    engine = ChaosEngine(provider="openai")
    
    topic = "The rise of lab-grown meat in fast food"
    print(f"📡 SCANNING NEWS FOR: {topic}...\n")

    # 1. Standard Run
    print("--- STANDARD DOOMER ---")
    res1 = engine.run(topic)
    print(f"Temp: {res1['temperature']} | Content: {res1['final_post'][:150]}...\n")

    # 2. Specific Persona
    print("--- THE ACCELERATIONIST ---")
    res2 = engine.run(topic, persona="The Accelerationist: Speed is everything. Ethics are secondary.")
    print(f"Temp: {res2['temperature']} | Content: {res2['final_post'][:150]}...\n")

    # 3. Randomized Chaos
    print("--- RANDOMIZED CHAOS ---")
    res3 = engine.run_randomized(topic)
    print(f"Persona: {res3['persona_used']}")
    print(f"Temp: {res3['temperature']} | Content: {res3['final_post'][:150]}...\n")

if __name__ == "__main__":
    main()