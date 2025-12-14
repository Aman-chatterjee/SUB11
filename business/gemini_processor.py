import google.generativeai as genai
import json


def translate_text_list(text_list, target_language, api_key, gemini_model, status_callback=None, indeterminate_callback=None):
    """
    Translates a list of text strings using Gemini.
    
    Args:
        text_list: List of text strings to translate
        target_language: Target language for translation
        api_key: Gemini API key
        gemini_model: Gemini model name
        status_callback: Optional callback for status updates
        indeterminate_callback: Optional callback for progress indicator
    
    Returns:
        List of translated text strings
    """
    try:
        if status_callback:
            status_callback(f"Translating with Gemini ({target_language})...")
        if indeterminate_callback:
            indeterminate_callback(True)
        
        genai.configure(api_key=api_key)
        input_json = json.dumps(text_list, ensure_ascii=False)
        
        prompt = f"""
        You are an expert linguistic processor and translator for SUBTITLE FILES.
        CRITICAL: This is for subtitle timing synchronization. You MUST return exactly the same number of text segments as provided.

        Your Goal:
        1. First, **CORRECT** any spelling or grammar mistakes in the source text.
        2. Then, **TRANSLATE** the corrected text to "{target_language}".

        STRICT OUTPUT RULES:
        - **IF Target is 'Hinglish':**
        - Translate to Hindi meaning.
        - MUST use **English Alphabet (Roman Script)**. 
        - Example: "Tum kaise ho?" (NOT "तुम कैसे हो")

        - **IF Target is 'Hindi':**
        - Translate to standard Hindi (Devanagari).
        - Example: "तुम कैसे हो?"

        - **IF Target is 'English':**
        - Correct the grammar/spelling. Do not translate if input is already English.

        - **FOR ALL OTHER LANGUAGES (Tamil, Telgu, Bangali, etc.):**
        - Translate to the **Standard Native Script** of that language.
        - Example (Kaise ho): "কেমন আছেন" (NOT "Kemon achen")

        INPUT DATA (JSON):
        {input_json}

        OUTPUT FORMAT:
        Return ONLY the raw JSON list of strings. No Markdown. No ```json``` tags.
        """
        model = genai.GenerativeModel(gemini_model)
        response = model.generate_content(prompt)
        
        # Parse JSON response
        result_text = response.text.strip()
        if "```" in result_text:
            result_text = result_text.replace("```json", "").replace("```", "").strip()
        
        translated = json.loads(result_text)
        
        if indeterminate_callback:
            indeterminate_callback(False)
        if status_callback:
            status_callback("✅ Translation completed")
        
        # Validate translation result
        if not isinstance(translated, list):
            raise Exception("Invalid response format from Gemini")
        
        if len(translated) != len(text_list):
            warning_msg = f"⚠️ Translation count mismatch: expected {len(text_list)}, got {len(translated)}"
            print(warning_msg)
        
        return translated
        
    except Exception as e:
        if indeterminate_callback:
            indeterminate_callback(False)
        error_msg = f"❌ Gemini error: {str(e)}"
        print(error_msg)
        if status_callback:
            status_callback(error_msg)
        raise
