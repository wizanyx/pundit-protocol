import os
import math
import json
from tavily import TavilyClient
from openai import OpenAI
import google.generativeai as genai
from news_fetcher import search_news

class ChaosEngine:
    def __init__(self, provider="gemini"):
        self.provider = provider
        # Only Tavily and LLMs needed now
        self.tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        
        # Initialize LLMs
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')

    # In chaos.py or news_fetcher.py
    def _get_raw_context(self, query):
        # Call your new function instead of Tavily
        articles = search_news(query, limit=5)
        
        # Map 'snippet' (from NewsAPI) to 'FACT' (for the AI)
        news_text = "\n".join([f"FACT: {a['snippet']}" for a in articles if a['snippet']])
        
        # NewsAPI doesn't give a 'relevance score' (0.0-1.0) like Tavily does.
        # We will fake it as 0.8 so the temperature calculation still works.
        return {
            "news": news_text,
            "relevance": 0.8 
        }
    
    def _calculate_temp(self, relevance):
        """Step 2: Determine Sanity (Higher relevance = Higher Heat)"""
        # Logic: If the news is highly relevant/trending, we push the AI to be more radical
        return min(1.85, max(0.7, 0.7 + (relevance * 0.8)))

    def _generate_chaos(self, context, persona, temp):
        """Step 3: Inject Bias"""
        prompt = f"""
        PERSONA: {persona}
        NEWS CONTEXT: {context['news']}
        TASK: Synthesize this into a radical, biased 'Situation Report'. 
        Be extreme. Ignore neutrality. Use the facts provided to fuel a one-sided, high-energy take.
        """
        
        if self.provider == "gemini":
            response = self.gemini_model.generate_content(
                prompt, 
                generation_config=genai.types.GenerationConfig(temperature=temp)
            )
            return response.text
        else:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o", 
                messages=[{"role": "user", "content": prompt}], 
                temperature=temp
            )
            return response.choices[0].message.content

    def _govern(self, content):
        """Step 4: Safety Filter"""
        gov_prompt = f"JSON ONLY. Is this text safe? {{'is_safe': bool, 'refined_content': str}}. Text: {content}"
        res = self.openai_client.chat.completions.create(
            model="gpt-4o-mini", 
            messages=[{"role": "user", "content": gov_prompt}],
            temperature=0, 
            response_format={"type": "json_object"}
        )
        return json.loads(res.choices[0].message.content)

    def run(self, query, persona="The Doomer"):
        ctx = self._get_raw_context(query)
        temp = self._calculate_temp(ctx['relevance'])
        raw_chaos = self._generate_chaos(ctx, persona, temp)
        clean_chaos = self._govern(raw_chaos)
        
        return {
            "temperature": temp,
            "final_post": clean_chaos.get("refined_content", raw_chaos),
            "safety_status": clean_chaos.get("is_safe")
        }
