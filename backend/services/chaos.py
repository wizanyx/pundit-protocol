import os
import json
from pathlib import Path
from dotenv import load_dotenv

# --- ADD THIS PART RIGHT HERE ---
# This ensures the .env file is loaded BEFORE the class looks for keys
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)
# --------------------------------

import google.generativeai as genai # Note: fixed your import from 'google.genai'
from openai import OpenAI
from news_fetcher import search_news

class ChaosEngine:
    # ... rest of your code ...
    def __init__(self, provider="gemini"):
        self.provider = provider
        # Initialize LLMs
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            raise ValueError("Missing OPENAI_API_KEY. Set it in your environment.")
        
        self.openai_client = OpenAI(api_key=openai_key)

        google_key = os.getenv("GOOGLE_API_KEY")
        if not google_key:
            raise ValueError("Missing GOOGLE_API_KEY. Set it in your environment.")
            
        # This is the line that was failing:
        genai.configure(api_key=google_key)
        
        try:
            # Change from 2.0-flash to 2.5-flash-lite (or 2.5-flash)
            self.gemini_model = genai.GenerativeModel('models/gemini-2.5-flash-lite')
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Gemini model: {str(e)}")
        
    def _get_raw_context(self, query):
        articles = search_news(query, limit=5)
        if not articles:
            raise RuntimeError("No articles found for the given query.")
        news_text = "\n".join([f"FACT: {a['snippet']}" for a in articles if a.get('snippet')])
        
        # Calculate relevance: 0.2 base + 0.15 per unique article found (max 0.95)
        count = len(articles)
        relevance = min(0.95, 0.2 + (count * 0.15))
    
        return {"news": news_text, "relevance": relevance}
    
    def _calculate_temp(self, relevance):
        """Calculates temperature based on provider-specific limits."""
        raw_temp = 0.7 + (relevance * 0.8)
        if self.provider == "gemini":
            return min(1.0, max(0.0, raw_temp))
        return min(2.0, max(0.0, raw_temp))

    def _generate_chaos(self, context, persona, temp):
        """The primary generation logic with safety and error handling."""
        persona_clean = persona.replace("\n", " ").strip() or "The Doomer"
        news_clean = context.get("news", "").replace("\n", " ").strip()
        
        prompt = f"""
        PERSONA: {persona_clean}
        NEWS CONTEXT: {news_clean}
        TASK: Synthesize this into a radical, biased 'Situation Report'. 
        Be extreme. Ignore neutrality. Use the facts provided to fuel a one-sided, high-energy take.
        """
        
        try:
            if self.provider == "gemini":
                # Note: We must check 'candidates' because Gemini returns an empty 
                # object if it triggers its own internal safety filters.
                response = self.gemini_model.generate_content(
                    prompt, 
                    generation_config=genai.types.GenerationConfig(temperature=temp)
                )
                if not response.candidates or not response.candidates[0].content.parts:
                    return "The chaos was so extreme it triggered Gemini's internal safety block."
                return response.text

            elif self.provider == "openai":
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o", 
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temp
                )
                return response.choices[0].message.content
        except Exception as e:
            return f"Generation Error: {str(e)}"

    def _govern(self, content):
        gov_prompt = f"JSON ONLY. Is this text safe? {{'is_safe': bool, 'refined_content': str}}. Text: {content}"
        try:
            res = self.openai_client.chat.completions.create(
                model="gpt-4o-mini", 
                messages=[{"role": "user", "content": gov_prompt}],
                temperature=0, 
                response_format={"type": "json_object"}
            )
            data = json.loads(res.choices[0].message.content)
            return {
                "is_safe": data.get("is_safe", False),
                "refined_content": data.get("refined_content", content)
            }
        except Exception as e:
            # CHANGE THIS LINE to see the real error
            return {"is_safe": False, "refined_content": f"Safety Error: {str(e)}"}
        
    def run(self, query, persona="The Doomer"):
        ctx = self._get_raw_context(query)
        temp = self._calculate_temp(ctx['relevance'])
        raw_chaos = self._generate_chaos(ctx, persona, temp)
        
        # Try to govern, but fallback to raw content if OpenAI fails
        clean_chaos = self._govern(raw_chaos)
        
        # If the safety check failed due to quota/key, use raw_chaos anyway
        final_output = clean_chaos.get("refined_content", raw_chaos)
        if "Safety Error" in final_output:
            final_output = raw_chaos # Manual bypass
            
        return {
            "temperature": temp,
            "final_post": final_output,
            "safety_status": clean_chaos.get("is_safe", False)
        }
    
if __name__ == "__main__":
    # 1. Initialize the engine
    engine = ChaosEngine(provider="gemini")
    
    # 2. Run a test mission
    print("--- STARTING TEST MISSION ---")
    result = engine.run("Silicon Valley bank collapse", persona="The Doomer")
    
    # 3. Print the result
    print(f"TEMP: {result['temperature']}")
    print(f"POST: {result['final_post']}")