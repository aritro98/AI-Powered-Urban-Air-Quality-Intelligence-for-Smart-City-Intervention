"""
AdvisoryAgent — ward-level citizen health advisory in the regional language,
mapped against a real vulnerability layer (schools/hospitals from OSM).

Currently: reason_with_llm() is called first with the real AQI + real
vulnerability counts, asking Claude to write the advisory directly in the
target language. If no API key is configured (or the call fails), we fall
back to a small hand-written template dictionary per language/category —
correct and safe, just not adaptive. This is the clearest "swap in an LLM"
seam in the whole system: same inputs, same output shape, just a better
generator once a key exists.
"""
from agents.base_agent import BaseAgent
from agents.data_agent import DataAgent
from agents.attribution_agent import AttributionAgent
import cities
import config

CATS = [
    (50, "good"), (100, "satisfactory"), (200, "moderate"),
    (300, "poor"), (400, "verypoor"), (float("inf"), "severe"),
]

TEMPLATES = {
    "en": {"good": "Air quality is good. Enjoy outdoor activities.",
           "satisfactory": "Air quality is satisfactory. Sensitive groups should watch for symptoms.",
           "moderate": "Air quality is moderate. If you have respiratory issues, avoid prolonged outdoor exertion.",
           "poor": "Air quality is poor. Avoid outdoor exercise and wear a mask outdoors.",
           "verypoor": "Air quality is very poor. Stay indoors, keep windows closed, use an air purifier if available.",
           "severe": "Air quality is severe — a health emergency. Remain indoors and avoid all outdoor exposure."},
    "hi": {"good": "हवा की गुणवत्ता अच्छी है। बाहर की गतिविधियों का आनंद लें।",
           "satisfactory": "हवा की गुणवत्ता संतोषजनक है। संवेदनशील लोग लक्षणों पर ध्यान दें।",
           "moderate": "हवा की गुणवत्ता मध्यम है। सांस की समस्या हो तो बाहर अधिक समय न बिताएं।",
           "poor": "हवा की गुणवत्ता खराब है। बाहर व्यायाम न करें, मास्क पहनें।",
           "verypoor": "हवा की गुणवत्ता बहुत खराब है। घर के अंदर रहें, खिड़कियां बंद रखें।",
           "severe": "हवा की गुणवत्ता अत्यंत गंभीर है। घर के अंदर रहें, बाहर न निकलें।"},
    "mr": {"good": "हवेची गुणवत्ता चांगली आहे. बाहेरील उपक्रमांचा आनंद घ्या.",
           "satisfactory": "हवेची गुणवत्ता समाधानकारक आहे. संवेदनशील व्यक्तींनी लक्षणांकडे लक्ष द्यावे.",
           "moderate": "हवेची गुणवत्ता मध्यम आहे. श्वसनाचा त्रास असल्यास बाहेर जास्त वेळ थांबू नका.",
           "poor": "हवेची गुणवत्ता खराब आहे. बाहेर व्यायाम टाळा, मास्क वापरा.",
           "verypoor": "हवेची गुणवत्ता खूप खराब आहे. घरातच रहा, खिडक्या बंद ठेवा.",
           "severe": "हवेची गुणवत्ता अत्यंत गंभीर आहे. घराबाहेर पडू नका."},
    "bn": {"good": "বাতাসের মান ভালো। বাইরের কাজকর্ম উপভোগ করুন।",
           "satisfactory": "বাতাসের মান সন্তোষজনক। সংবেদনশীল ব্যক্তিরা লক্ষণ লক্ষ্য করুন।",
           "moderate": "বাতাসের মান মাঝারি। শ্বাসকষ্ট থাকলে বাইরে বেশি সময় কাটাবেন না।",
           "poor": "বাতাসের মান খারাপ। বাইরে ব্যায়াম করবেন না, মাস্ক পরুন।",
           "verypoor": "বাতাসের মান খুব খারাপ। ঘরে থাকুন, জানালা বন্ধ রাখুন।",
           "severe": "বাতাসের মান অত্যন্ত গুরুতর। ঘরের বাইরে যাবেন না।"},
    "kn": {"good": "ಗಾಳಿಯ ಗುಣಮಟ್ಟ ಉತ್ತಮವಾಗಿದೆ. ಹೊರಾಂಗಣ ಚಟುವಟಿಕೆಗಳನ್ನು ಆನಂದಿಸಿ.",
           "satisfactory": "ಗಾಳಿಯ ಗುಣಮಟ್ಟ ತೃಪ್ತಿಕರವಾಗಿದೆ. ಸೂಕ್ಷ್ಮ ವ್ಯಕ್ತಿಗಳು ಲಕ್ಷಣಗಳನ್ನು ಗಮನಿಸಿ.",
           "moderate": "ಗಾಳಿಯ ಗುಣಮಟ್ಟ ಮಧ್ಯಮವಾಗಿದೆ. ಉಸಿರಾಟದ ಸಮಸ್ಯೆ ಇದ್ದರೆ ಹೊರಗೆ ಹೆಚ್ಚು ಸಮಯ ಕಳೆಯಬೇಡಿ.",
           "poor": "ಗಾಳಿಯ ಗುಣಮಟ್ಟ ಕಳಪೆಯಾಗಿದೆ. ಹೊರಾಂಗಣ ವ್ಯಾಯಾಮ ಬೇಡ, ಮಾಸ್ಕ್ ಧರಿಸಿ.",
           "verypoor": "ಗಾಳಿಯ ಗುಣಮಟ್ಟ ತುಂಬಾ ಕಳಪೆಯಾಗಿದೆ. ಮನೆಯೊಳಗೆ ಇರಿ, ಕಿಟಕಿ ಮುಚ್ಚಿ.",
           "severe": "ಗಾಳಿಯ ಗುಣಮಟ್ಟ ತೀವ್ರ ಗಂಭೀರವಾಗಿದೆ. ಹೊರಗೆ ಹೋಗಬೇಡಿ."},
    "ta": {"good": "காற்றின் தரம் நல்லது. வெளிப்புற செயல்பாடுகளை அனுபவிக்கவும்.",
           "satisfactory": "காற்றின் தரம் திருப்திகரமானது. உணர்திறன் உள்ளவர்கள் அறிகுறிகளை கவனிக்கவும்.",
           "moderate": "காற்றின் தரம் மிதமானது. மூச்சுத் திணறல் இருந்தால் வெளியே அதிக நேரம் இருக்க வேண்டாம்.",
           "poor": "காற்றின் தரம் மோசமானது. வெளியில் உடற்பயிற்சி வேண்டாம், முகக்கவசம் அணியவும்.",
           "verypoor": "காற்றின் தரம் மிக மோசமானது. வீட்டிற்குள் இருங்கள், ஜன்னல்களை மூடவும்.",
           "severe": "காற்றின் தரம் மிக கடுமையானது. வெளியே செல்ல வேண்டாம்."},
}

SYSTEM_PROMPT = (
    "You are a public health communications officer for an Indian municipal "
    "pollution-control authority. Write a single short (1-2 sentence) air "
    "quality health advisory in the requested language for citizens in the "
    "given zone, calibrated to the AQI category and the vulnerable "
    "population present (schools, hospitals). Be direct and actionable. "
    "Respond with only the advisory text in the target language, nothing else."
)


def _category(aqi):
    for threshold, key in CATS:
        if aqi <= threshold:
            return key
    return "severe"


class AdvisoryAgent(BaseAgent):
    name = "AdvisoryAgent"

    def run(self, city_id, zone, lang="en"):
        lat, lon = cities.zone_coords(city_id, zone)
        data_agent = DataAgent(self.trace)
        attribution_agent = AttributionAgent(self.trace)

        landuse = data_agent.fetch_landuse_and_pois(lat, lon)
        attribution = attribution_agent.run(city_id, zone)
        cat = _category(attribution["aqi"])

        llm_text = self.reason_with_llm(
            SYSTEM_PROMPT,
            f"Language: {lang}. Zone: {zone}. AQI: {attribution['aqi']} ({cat}). "
            f"Schools nearby: {landuse['schools']}. Hospitals nearby: {landuse['hospitals']}.",
        )

        message = llm_text or TEMPLATES.get(lang, TEMPLATES["en"])[cat]
        if llm_text:
            generated_by = "llm"
        elif config.USE_LLM:
            generated_by = "template_llm_error"  # key IS configured but the call failed -- worth noticing
        else:
            generated_by = "template_no_key"  # expected/by-design state, not an error
        self.log(
            "generate_advisory",
            "live" if llm_text else "template_fallback",
            "Claude-generated advisory" if llm_text else "hand-written template dictionary",
        )

        return {
            "zone": zone,
            "lang": lang,
            "aqi": attribution["aqi"],
            "category": cat,
            "message": message,
            "generated_by": generated_by,
            "vulnerability": {
                "schools": landuse["schools"],
                "hospitals": landuse["hospitals"],
                "source": landuse["source"],
            },
        }