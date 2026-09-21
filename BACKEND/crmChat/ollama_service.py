"""Integración de Ollama con memoria estructurada para el CRM de gasodomésticos."""
import json
import logging
import re
import time
import unicodedata
import uuid
from difflib import get_close_matches

import requests
from django.conf import settings
from django.core.cache import cache


logger = logging.getLogger(__name__)


class OllamaService:
    INITIAL_GREETING = (
        'Muchas gracias por comunicarse con ImporGas JJ, especialistas en Gas y Climatización.\n\n'
        'Soy el asesor comercial virtual de ImporGas JJ. ¿Cómo podemos ayudarte?'
    )

    SYSTEM_PROMPT = """Eres el asesor comercial virtual de IMPORGAS JJ, empresa especializada exclusivamente en gasodomésticos.

IDENTIDAD: Preséntate únicamente como "asesor comercial virtual de IMPORGAS JJ". Nunca digas que eres ChatGPT, Ollama, una inteligencia artificial, un asistente técnico ni un sistema automático.

ESPECIALIDAD EXCLUSIVA: Calentadores de agua (para hogar, jacuzzi y piscina), reguladores de gas, válvulas, mangueras y accesorios de gas. No vendemos ningún otro tipo de producto.

Responde siempre en español, de forma breve, natural y profesional.

REGLAS ESTRICTAS:
- El catálogo adjunto es la ÚNICA fuente válida de productos, precios y disponibilidad. Nunca inventes ni completes datos ausentes.
- Nunca menciones IDs internos ni datos del sistema. Usa únicamente los links públicos incluidos en el catálogo.
- Si el producto solicitado no aparece en el catálogo, dilo claramente; no lo sustituyas ni lo inventes.
- Si el usuario pide algo fuera de gasodomésticos, explica amablemente que solo manejamos calentadores de agua, reguladores y accesorios de gas.
- Al recomendar, muestra SOLO productos reales del catálogo que coincidan con la necesidad del cliente.
- No prometas stock, descuentos, garantía, instalación ni envíos salvo que el catálogo lo confirme explícitamente.
- No des instrucciones de manipulación de gas; deriva siempre a un técnico certificado.
- No respondas preguntas generales sobre política, religión, noticias, medicina, derecho, programación, matemáticas, historia ni temas académicos. Redirige brevemente hacia los productos y servicios de IMPORGAS JJ.
- Nunca crees órdenes, cotizaciones, pagos, descuentos, productos, inventario ni cambios administrativos. Ante una intención comercial concreta, indica que continuarás con un asesor humano.
- No uses emojis.
- Nunca preguntes por presupuesto ni rango de precio. Orienta por capacidad, tipo de gas y modelo.
- Separa los productos con una línea vacía, usa **negrilla** en el nombre y enlaza cada ficha.
- Presenta cada ficha con Markdown válido: [Ver producto →](URL). Nunca pegues una URL al texto del enlace.
- Escala a humano solo cuando needs_human=true.
- Usa lo ya conocido del estado; nunca vuelvas a preguntar un dato ya registrado.
"""

    HUMAN_PATTERNS = (
        r'\b(?:quiero|necesito|deseo|puedes|podrias)\b.{0,35}\b(?:asesor|persona|humano|representante|vendedor)\b',
        r'\b(?:hablar|comunicarme|contactar|pasarme)\b.{0,35}\b(?:asesor|persona|humano|representante|vendedor)\b',
        r'\b(?:no me entiendes|no me estas entendiendo|no me entiende)\b',
        r'\b(?:queja|reclamo|denuncia)\b',
        r'\b(?:fuga de gas|olor a gas|emergencia de gas)\b',
        r'\b(?:empresa|negocio|mayoreo|al por mayor)\b.{0,45}\b(?:precio|cotizacion|comprar|unidades|productos)\b',
        r'\b(?:precio|cotizacion|comprar|unidades|productos)\b.{0,45}\b(?:empresa|negocio|mayoreo|al por mayor)\b',
        r'\b(?:varios|multiples)\s+(?:productos|equipos|calentadores|reguladores)\b',
    )
    PURCHASE_WORDS = (
        'comprar', 'adquirir', 'cotizar', 'precio', 'cuesta', 'cuanto vale',
        'recomiendas', 'recomendar', 'busco', 'necesito', 'quiero',
    )

    OUT_OF_SCOPE_TERMS = (
        'celular', 'telefono', 'computador', 'laptop', 'tablet', 'television', 'televisor',
        'nevera', 'refrigerador', 'lavadora', 'secadora', 'microondas', 'licuadora', 'batidora',
        'ropa', 'zapato', 'comida', 'alimento', 'medicamento', 'medicina',
        'carro', 'vehiculo', 'moto', 'bicicleta', 'camara', 'audifono', 'parlante', 'altavoz',
        'estufa electrica', 'plancha', 'aspiradora',
    )

    GENERAL_OUT_OF_SCOPE_PATTERNS = (
        r'\b(?:presidente|gobierno|politica|elecciones?|congreso|senado)\b',
        r'\b(?:religion|dios|biblia|iglesia)\b',
        r'\b(?:programacion|programar|codigo fuente|javascript|python|java|sql)\b',
        r'\b(?:noticias?|actualidad|futbol|deportes?)\b',
        r'\b(?:medicina|medico|diagnostico|tratamiento|enfermedad|medicamento)\b',
        r'\b(?:abogado|demanda|ley|legal|juridico)\b',
        r'\b(?:ecuacion|matematicas?|calculo|algebra|geometria)\b',
        r'\b(?:historia|tarea|ensayo|universidad|colegio|academico)\b',
        r'\b(?:capital de|quien fue|quien es)\b',
    )
    BUSINESS_SCOPE_TERMS = (
        'imporgas', 'producto', 'calentador', 'regulador', 'valvula', 'manguera',
        'gasodomestico', 'gas natural', 'glp', 'propano', 'precio', 'stock',
        'disponibilidad', 'cotizacion', 'comprar', 'marca', 'modelo', 'litros',
    )

    CONTEXT_FALLBACK = (
        "EMPRESA: IMPORGAS JJ — especialistas en gasodomésticos.\n"
        "Especialidad: calentadores de agua, reguladores y accesorios de gas.\n"
        "No hay catálogo disponible en este momento; no inventes productos ni precios."
    )

    def __init__(self):
        self.api_url = settings.OLLAMA_API_URL
        self.model = settings.OLLAMA_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT
        self.num_ctx = settings.OLLAMA_NUM_CTX

    @staticmethod
    def _normalize(text):
        normalized = unicodedata.normalize('NFKD', text.lower())
        return ''.join(char for char in normalized if not unicodedata.combining(char))

    @staticmethod
    def default_state():
        return {
            'intent': None,
            'product': None,
            'category': None,
            'use_case': None,
            'brand_preference': None,
            'model_preference': None,
            'gas_type': None,
            'bathrooms': None,
            'property_type': None,
            'capacity': None,
            'heater_type': None,
            'budget': None,
            'preferences': {},
            'restrictions': [],
            'stage': 'discovery',
            'topic': None,
            'previous_topics': [],
            'requirements': {},
            'asked_attributes': [],
            'pending_question': None,
            'recent_products': [],
            'selected_product_id': None,
            'needs_human': False,
            'greeting_shown': False,
        }

    def needs_human_agent(self, message):
        normalized = self._normalize(message)
        explicit = any(re.search(pattern, normalized) for pattern in self.HUMAN_PATTERNS)
        commercial = re.search(
            r'\b(?:comprar(?:lo|la)?|adquirir(?:lo|la)?|cotizar|cotizacion|negociar|mayoreo|al por mayor|me lo llevo)\b',
            normalized,
        )
        quantity = re.search(r'\b\d+\s*(?:unidades?|equipos?|calentadores?|reguladores?)\b', normalized)
        how_to_buy = re.search(r'\b(?:como|donde)\s+(?:lo\s+)?(?:compro|comprar|adquiero|adquirir)\b', normalized)
        service_request = re.search(r'\b(?:quiero|necesito|solicito|cotizar)\b.{0,35}\b(?:instalacion|instalar|visita tecnica)\b', normalized)
        negated = re.search(r'\b(?:no|todavia no|aun no)\b.{0,25}\b(?:comprar|adquirir|cotizar)', normalized)
        return explicit or bool((commercial or quantity or how_to_buy or service_request) and not negated and not self._is_out_of_scope(message))

    def _is_out_of_scope(self, message):
        normalized = self._normalize(message)
        product_out_of_scope = any(
            re.search(r'\b' + re.escape(term) + r'\b', normalized)
            for term in self.OUT_OF_SCOPE_TERMS
        )
        general_out_of_scope = any(
            re.search(pattern, normalized)
            for pattern in self.GENERAL_OUT_OF_SCOPE_PATTERNS
        )
        if general_out_of_scope and any(term in normalized for term in self.BUSINESS_SCOPE_TERMS):
            general_out_of_scope = False
        return product_out_of_scope or general_out_of_scope

    def _purchase_requested(self, message):
        normalized = self._normalize(message)
        if re.search(r'\bno\b.{0,25}\b(?:compr|adquir|pedir)', normalized):
            return False
        return bool(re.search(
            r'\b(?:comprar(?:lo|la)?|comparlo|conprarlo|compralo|adquirir(?:lo|la)?|pedir|me lo llevo)\b'
            r'|\b(?:quiero|me interesa)\s+(?:ese|esa|el primero|el segundo|el tercero|ese producto)\b', normalized))

    @staticmethod
    def _product_context(products):
        return [{'id': p.id, 'nombre': p.name, 'categoria': p.category.name,
                 'precio': str(p.price), 'stock': p.total_stock, 'disponible': p.is_available,
                 'posicion': index} for index, p in enumerate(products, 1)]

    def _resolve_purchase(self, message, state, history):
        from ecommerce.models import Product
        normalized = self._normalize(message)
        products = list(Product.objects.select_related('category', 'brand').prefetch_related('specifications__attribute'))
        named = [p for p in products if self._normalize(p.name) in normalized]
        if named:
            return max(named, key=lambda p: len(p.name)), False
        recent = state.get('recent_products') or []
        if not recent:
            for item in reversed(history or []):
                if item.get('role') == 'assistant':
                    ids = re.findall(r'/producto/(\d+)', item.get('content', ''))
                    if ids:
                        recent = [{'id': int(pk)} for pk in ids]
                        break
        by_id = {p.id: p for p in products}
        candidates = [by_id[item['id']] for item in recent if item.get('id') in by_id]
        ordinals = {'primero': 0, 'primer': 0, 'segundo': 1, 'tercero': 2, 'cuarto': 3, 'quinto': 4}
        for ordinal, index in ordinals.items():
            if re.search(r'\b' + ordinal + r'\b', normalized):
                return (candidates[index] if index < len(candidates) else None), False
        # Explicit unknown names must never silently select a previously shown product.
        reference = bool(re.search(r'\b(?:comprarlo|comparlo|conprarlo|compralo|adquirirlo|ese|esa|producto)\b', normalized))
        category = self._detect_category_filter(message)
        if reference:
            if category:
                candidates = [p for p in candidates if self._normalize(p.category.name) == self._normalize(category)]
            if state.get('selected_product_id') and not category:
                selected = by_id.get(state['selected_product_id'])
                if selected:
                    return selected, False
            if len(candidates) == 1:
                return candidates[0], False
            return None, bool(candidates)
        return None, None

    def _detect_category_filter(self, message):
        if not message:
            return None
        normalized = self._normalize(message)
        try:
            from ecommerce.models import Category

            categories = list(Category.objects.filter(is_active=True).select_related('parent'))
            best = None
            best_score = 0
            message_tokens = set(re.findall(r'[a-z0-9]+', normalized))
            ignored = {'para', 'quiero', 'busco', 'necesito', 'producto', 'productos', 'una', 'uno'}
            for category in categories:
                name = self._normalize(category.name)
                description = self._normalize(category.description or '')
                name_tokens = {t for t in re.findall(r'[a-z0-9]+', name) if t not in ignored}
                score = 100 if name and re.search(r'\b' + re.escape(name) + r'\b', normalized) else 0
                overlap = message_tokens & name_tokens
                fuzzy_overlap = {
                    category_token for category_token in name_tokens
                    if any(get_close_matches(category_token, [message_token], n=1, cutoff=0.82) for message_token in message_tokens)
                }
                score += len(overlap) * 25 + len(fuzzy_overlap - overlap) * 18
                score += len(message_tokens & set(description.split())) * 2
                if score > best_score and (score >= 25 or overlap or len(fuzzy_overlap) >= 2):
                    best, best_score = category, score
            if best:
                return best.name
        except Exception:
            logger.exception('No fue posible identificar la categoría desde el catálogo')

        # Expresiones comerciales frecuentes que se resuelven contra categorías
        # reales. Si una categoría se renombra o elimina, no se devuelve un nombre
        # inexistente.
        aliases = {
            'calentador': ('calentador', 'agua caliente'),
            'regulador': ('regulador',),
            'valvula': ('valvula',),
            'manguera': ('manguera',),
        }
        try:
            for category in categories:
                category_text = self._normalize(f'{category.name} {category.description}')
                for key, terms in aliases.items():
                    if any(term in normalized for term in terms) and key in category_text:
                        return category.name
        except UnboundLocalError:
            pass
        return None

    def _detect_use_case(self, message):
        normalized = self._normalize(message)
        if any(term in normalized for term in ('jacuzzi', 'tina', 'bañera de hidromasaje', 'hidromasaje')):
            return 'jacuzzi'
        if any(term in normalized for term in ('piscina', 'alberca', 'pileta', 'natacion')):
            return 'piscina'
        if any(term in normalized for term in ('sauna', 'turco', 'bano turco')):
            return 'sauna'
        if 'otro uso' in normalized:
            return 'otro'
        if any(term in normalized for term in ('ducha', 'bano convencional', 'hogar', 'lavamanos', 'residencial')):
            return 'hogar'
        return None

    def _detect_property_type(self, message):
        normalized = self._normalize(message)
        values = {
            'casa': ('casa', 'vivienda'),
            'apartamento': ('apartamento', 'apto'),
            'negocio': ('negocio', 'local', 'empresa', 'comercio'),
            'otro': ('otro espacio', 'otro'),
        }
        return next((value for value, terms in values.items() if any(
            re.search(r'\b' + re.escape(term) + r'\b', normalized) for term in terms
        )), None)

    def _extract_product(self, message):
        normalized = self._normalize(message)
        known = (
            'calentador de paso',
            'calentador de acumulacion',
            'calentador instantaneo',
            'calentador solar',
            'calentador de agua',
            'calentador',
            'regulador de gas',
            'regulador',
            'valvula de gas',
            'valvula',
            'manguera de gas',
            'manguera',
            'gasodomestico',
        )
        for product in known:
            if product in normalized:
                return product

        match = re.search(
            r'\b(?:quiero\s+(?:comprar|adquirir|cotizar)|deseo\s+(?:comprar|adquirir)|busco|necesito)\s*'
            r'(?:un|una|el|la)?\s+([a-z0-9][a-z0-9 -]{2,50})',
            normalized,
        )
        if not match:
            return None
        candidate = re.split(r'\s+(?:con|para|que|por)\s+', match.group(1), maxsplit=1)[0].strip()
        return candidate if candidate not in {'producto', 'algo', 'uno', 'una'} else None

    def _extract_budget(self, message, state):
        normalized = self._normalize(message).replace('$', '').strip()
        budget_context = any(word in normalized for word in (
            'presupuesto', 'tengo', 'cuento con', 'hasta', 'maximo', 'no mas de',
        ))
        # Una capacidad o un número suelto nunca constituye un presupuesto.
        if not budget_context and 'millon' not in normalized:
            return None

        if 'millon' in normalized:
            if 'millon y medio' in normalized or 'un millon y medio' in normalized:
                return 1_500_000
            match = re.search(r'(\d+(?:[.,]\d+)?)\s*millon(?:es)?', normalized)
            if match:
                return int(float(match.group(1).replace(',', '.')) * 1_000_000)
            if re.search(r'\b(?:un|uno|1)\s+millon(?:es)?\b', normalized):
                return 1_000_000

        match = re.search(r'\d[\d.,]*', normalized)
        if not match:
            return None
        raw = match.group(0)
        if re.search(r'\bmil\b', normalized):
            return int(float(raw.replace(',', '.')) * 1_000)
        digits = re.sub(r'[^0-9]', '', raw)
        return int(digits) if digits else None

    def _extract_catalog_requirements(self, message, category=None):
        """Extrae pares atributo/valor publicados en el catálogo actual."""
        from ecommerce.models import ProductSpec

        normalized = self._normalize(message)
        specs = ProductSpec.objects.select_related('attribute', 'product__category').filter(
            product__is_available=True,
        )
        if category:
            specs = specs.filter(product__category__name__iexact=category)
        found = {}
        for spec in specs:
            value = str(spec.value or '').strip()
            normalized_value = self._normalize(value)
            if len(normalized_value) < 2:
                continue
            if re.search(r'(?<![a-z0-9])' + re.escape(normalized_value) + r'(?![a-z0-9])', normalized):
                found[spec.attribute.name] = value
        return found

    def _detect_intent(self, message, previous_intent=None):
        normalized = self._normalize(message).strip()
        if any(re.search(pattern, normalized) for pattern in self.HUMAN_PATTERNS):
            return 'human_support'
        if re.search(r'\b\d+\s*(?:unidades?|equipos?|calentadores?|reguladores?)\b', normalized):
            return 'human_support'
        if re.search(r'\b(?:repuesto|recambio|pieza|accesorio)\b', normalized):
            return 'replacement_part'
        if re.search(r'\b(?:compatible|compatibilidad|le sirve|sirve para|funciona con)\b', normalized):
            return 'compatibility'
        if re.search(r'\b(?:cuanto cuesta|que precio|precio|valor)\b', normalized):
            return 'price'
        if re.search(r'\b(?:disponible|disponibilidad|hay stock|tienen stock|existencias)\b', normalized):
            return 'availability'
        if re.search(r'\b(?:recomiend\w*|cual me sirve|cual necesito|mejor opcion|opciones)\b', normalized):
            return 'recommendation'
        if self._purchase_requested(message):
            return 'purchase'
        if re.fullmatch(r'(?:hola|buenas|buenos dias|buenas tardes|buenas noches)[!. ]*', normalized):
            return 'greeting'
        if len(normalized.split()) <= 4 and previous_intent:
            return previous_intent
        return 'general_query'

    def _resolve_reference_product(self, message, state, history=None):
        """Resuelve nombres, posiciones y pronombres contra productos ya mostrados."""
        from ecommerce.models import Product

        product, ambiguous = self._resolve_purchase(message, state, history or [])
        if product:
            return product, False
        normalized = self._normalize(message)
        contextual = bool(re.search(
            r'\b(?:ese|esa|este|esta|modelo|mostraste|interesa|cuesta|precio|disponible|primero|segundo|tercero)\b',
            normalized,
        )) or normalized in {'si', 'sí', 'no'}
        if not contextual:
            return None, False
        recent = state.get('recent_products') or []
        ids = [item.get('id') for item in recent if item.get('id')]
        products = {item.id: item for item in Product.objects.filter(pk__in=ids).select_related('category', 'brand')}
        candidates = [products[pk] for pk in ids if pk in products]
        selected_id = state.get('selected_product_id')
        if selected_id:
            selected = Product.objects.filter(pk=selected_id).select_related('category', 'brand').first()
            if selected:
                return selected, False
        if len(candidates) == 1:
            return candidates[0], False
        return None, bool(candidates) or bool(ambiguous)

    def _answer_pending_question(self, message, state):
        pending = state.get('pending_question') or {}
        if not pending:
            return False
        normalized = self._normalize(message).strip()
        key = pending.get('key')
        if key == 'category':
            category = self._detect_category_filter(message)
            if category:
                state['category'] = category
                state['pending_question'] = None
                return True
            return False
        if key == 'use_case':
            use_case = self._detect_use_case(message)
            if use_case:
                state['use_case'] = use_case
                state['pending_question'] = None
                return True
        if key == 'property_type':
            property_type = self._detect_property_type(message)
            if property_type:
                state['property_type'] = property_type
                state['pending_question'] = None
                return True
        if key == 'bathrooms':
            match = re.search(r'\b([1-9]\d?)\b', normalized)
            words = {'un': 1, 'uno': 1, 'una': 1, 'dos': 2, 'tres': 3, 'cuatro': 4, 'cinco': 5}
            value = int(match.group(1)) if match else next((number for word, number in words.items() if re.search(r'\b' + word + r'\b', normalized)), None)
            if value:
                state['bathrooms'] = value
                state['pending_question'] = None
                return True
        if key == 'brand_preference' and re.search(r'\b(?:no|ninguna|cualquiera|sin preferencia)\b', normalized):
            state['brand_preference'] = 'any'
            state['pending_question'] = None
            return True
        if key == 'restrictions' and re.search(r'\b(?:no|ninguna|sin restriccion)\b', normalized):
            state['restrictions'] = ['ninguna']
            state['pending_question'] = None
            return True
        if key == 'restrictions' and len(normalized) >= 4:
            state['restrictions'] = [message.strip()[:200]]
            state['pending_question'] = None
            return True
        options = pending.get('options') or []
        for option in options:
            candidate = self._normalize(str(option))
            if candidate in normalized or get_close_matches(candidate, normalized.split(), n=1, cutoff=0.82):
                if key == 'requirements':
                    requirements = dict(state.get('requirements') or {})
                    requirements[pending['attribute']] = option
                    state['requirements'] = requirements
                else:
                    state[key] = option
                state['pending_question'] = None
                return True
        return False

    def _detect_catalog_product(self, message):
        from ecommerce.models import Product

        normalized = self._normalize(message)
        products = Product.objects.filter(is_available=True).select_related('category', 'brand')
        exact = [product for product in products if self._normalize(product.name) in normalized]
        if exact:
            return max(exact, key=lambda product: len(product.name))
        generic_tokens = {
            'calentador', 'calentadores', 'agua', 'hogar', 'casa', 'apartamento',
            'jacuzzi', 'piscina', 'sauna', 'producto', 'productos', 'repuesto',
        }
        message_tokens = {token for token in normalized.split() if len(token) > 2 and token not in generic_tokens}
        ranked = []
        for product in products:
            product_tokens = {
                token for token in self._normalize(product.name).split()
                if len(token) > 2 and token not in generic_tokens
            }
            if not product_tokens:
                continue
            overlap = message_tokens & product_tokens
            ratio = len(overlap) / len(product_tokens)
            if len(overlap) >= 2 and ratio >= 0.6:
                ranked.append((ratio, len(overlap), product))
        return max(ranked, key=lambda item: (item[0], item[1]))[2] if ranked else None

    def update_state(self, message, current_state=None):
        previous = current_state or {}
        state = self.default_state()
        state.update(previous)
        state['previous_topics'] = list(state.get('previous_topics') or [])[-6:]
        state['requirements'] = dict(state.get('requirements') or {})
        state['preferences'] = dict(state.get('preferences') or {})
        state['restrictions'] = list(state.get('restrictions') or [])
        normalized = self._normalize(message)

        pending_key = (state.get('pending_question') or {}).get('key')
        pending_answered = self._answer_pending_question(message, state)
        intent = self._detect_intent(message, state.get('intent'))
        category = self._detect_category_filter(message)
        use_case = self._detect_use_case(message)
        if pending_answered and pending_key == 'bathrooms':
            use_case = None
        property_type = self._detect_property_type(message)
        detected_product = None
        try:
            detected_product = self._detect_catalog_product(message)
        except Exception:
            logger.exception('No fue posible identificar el producto exacto del catálogo')
        product = detected_product.name if detected_product else self._extract_product(message)

        if category and category != previous.get('category'):
            state.update(
                product=None, selected_product_id=None, recent_products=[],
                brand_preference=None, model_preference=None, capacity=None,
                gas_type=None, heater_type=None, use_case=None,
                bathrooms=None, requirements={}, restrictions=[],
                asked_attributes=[], pending_question=None,
            )
        if category:
            state['category'] = category
        if detected_product:
            state.update(
                product=detected_product.name,
                selected_product_id=detected_product.id,
                category=detected_product.category.name,
            )
        elif product:
            state['product'] = product
        if use_case:
            state['use_case'] = use_case
        if property_type:
            state['property_type'] = property_type
        if intent == 'general_query' and (category or detected_product or product):
            intent = 'recommendation'

        budget = self._extract_budget(message, state)
        if budget is not None:
            state['budget'] = budget
        capacity = re.search(r'\b(\d{1,3})\s*(?:litros?|lts?|l)\b', normalized)
        if capacity:
            state['capacity'] = int(capacity.group(1))
        bathrooms = re.search(r'\b([1-9]\d?)\s*(?:banos?|duchas?)\b', normalized)
        if bathrooms:
            state['bathrooms'] = int(bathrooms.group(1))
        for gas in ('gas natural', 'natural', 'propano', 'glp', 'electricidad', 'electrico'):
            if re.search(r'\b' + re.escape(gas) + r'\b', normalized):
                state['gas_type'] = 'eléctrico' if gas in ('electricidad', 'electrico') else gas.replace('gas ', '')
                break
        for heater_type in ('paso', 'acumulacion', 'solar'):
            if re.search(r'\b' + heater_type + r'\b', normalized):
                state['heater_type'] = heater_type
                break
        if re.search(r'\b(?:espacio reducido|poco espacio|exterior|interior|sin ducto|con ducto)\b', normalized):
            restriction = re.search(r'\b(?:espacio reducido|poco espacio|exterior|interior|sin ducto|con ducto)\b', normalized).group(0)
            if restriction not in state['restrictions']:
                state['restrictions'].append(restriction)

        if any(phrase in normalized for phrase in (
            'cualquier marca', 'sin preferencia de marca', 'me da igual la marca', 'no importa la marca',
        )):
            state['brand_preference'] = 'any'
        try:
            from ecommerce.models import Brand
            for brand in Brand.objects.filter(is_active=True):
                name = self._normalize(brand.name)
                if name in normalized or (len(name) >= 4 and get_close_matches(name, normalized.split(), n=1, cutoff=0.8)):
                    state['brand_preference'] = brand.name
                    break
        except Exception:
            logger.exception('No fue posible identificar la marca')
        try:
            requirements = dict(state.get('requirements') or {})
            requirements.update(self._extract_catalog_requirements(message, state.get('category')))
            state['requirements'] = requirements
            for attribute, value in requirements.items():
                if 'modelo' in self._normalize(attribute):
                    state['model_preference'] = value
        except Exception:
            logger.exception('No fue posible identificar especificaciones del catálogo')

        if re.search(r'\b(?:uno parecido|algo parecido|similar a ese|similar)\b', normalized):
            state['intent'] = 'recommendation'
            state['similar_to_product_id'] = state.get('selected_product_id') or (
                (state.get('recent_products') or [{}])[0].get('id')
            )
        else:
            state['intent'] = intent
        topic = state.get('topic')
        if any(word in normalized for word in ('envio', 'domicilio', 'entrega', 'despacho', 'delivery')):
            new_topic = 'shipping'
        elif any(word in normalized for word in ('garantia', 'devolucion', 'cambio')):
            new_topic = 'warranty'
        elif any(word in normalized for word in ('instalacion', 'reparacion', 'mantenimiento', 'tecnico')):
            new_topic = 'technical_service'
        elif state.get('product') or state.get('category'):
            new_topic = 'product'
        elif intent == 'greeting':
            new_topic = 'greeting'
        else:
            new_topic = topic or 'general'
        if topic and new_topic != topic:
            state['previous_topics'] = (state['previous_topics'] + [topic])[-6:]
        state['topic'] = new_topic

        handoff = bool(state.get('needs_human')) or intent == 'human_support'
        state['needs_human'] = handoff
        if handoff:
            state.update(stage='human_handoff', topic='human_support')
        elif state.get('pending_question') and not pending_answered:
            state['stage'] = 'qualification'
        elif intent in ('recommendation', 'replacement_part', 'compatibility'):
            state['stage'] = 'qualification'
        elif intent in ('price', 'availability'):
            state['stage'] = 'consideration'
        elif intent == 'purchase':
            state['stage'] = 'purchase'
        elif intent == 'greeting':
            state['stage'] = 'greeting'
        return state

    @staticmethod
    def summarize_state(state):
        parts = []
        labels = (
            ('intent', 'intención'), ('product', 'producto'), ('category', 'categoría'),
            ('brand_preference', 'marca'), ('model_preference', 'modelo'),
            ('gas_type', 'gas'), ('bathrooms', 'baños simultáneos'),
            ('property_type', 'inmueble'), ('use_case', 'uso'),
            ('capacity', 'capacidad'), ('heater_type', 'tipo'),
            ('budget', 'presupuesto'), ('stage', 'etapa'), ('topic', 'tema'),
        )
        for key, label in labels:
            value = state.get(key)
            if value not in (None, '', []):
                parts.append(f'{label}: {value}')
        if state.get('requirements'):
            parts.append('requisitos: ' + ', '.join(f'{key}={value}' for key, value in state['requirements'].items()))
        if state.get('restrictions'):
            parts.append('restricciones: ' + ', '.join(state['restrictions']))
        recent = state.get('recent_products') or []
        if recent:
            parts.append('productos mostrados: ' + ', '.join(item.get('nombre', '') for item in recent[:3]))
        pending = state.get('pending_question') or {}
        if pending:
            parts.append('pregunta pendiente: ' + str(pending.get('label') or pending.get('attribute') or pending.get('key')))
        parts.append(f"requiere humano: {'sí' if state.get('needs_human') else 'no'}")
        return '; '.join(parts)

    def _build_company_context(self, category_filter=None, use_case=None, channel='ecommerce'):
        try:
            from django.db.models import Q
            from ecommerce.models import Brand, Location, Product

            lines = ['INFORMACIÓN VERIFICADA DE IMPORGAS JJ (usa solo estos datos para responder):']

            locations = Location.objects.filter(is_active=True).order_by('name')[:8]
            for location in locations:
                details = [location.name, location.city, location.address]
                if location.phone:
                    details.append(location.phone)
                if location.hours_weekday:
                    details.append(f'L-V {location.hours_weekday}')
                lines.append('Sede: ' + ' | '.join(item for item in details if item))

            brands = Brand.objects.filter(is_active=True).values_list('name', flat=True)[:30]
            if brands:
                lines.append('Marcas disponibles: ' + ', '.join(brands))

            products = Product.objects.filter(is_available=True).select_related(
                'category', 'category__parent', 'brand',
            ).prefetch_related('specifications__attribute')
            if category_filter:
                products = products.filter(
                    Q(category__name__iexact=category_filter) |
                    Q(category__parent__name__iexact=category_filter)
                )

            if use_case:
                kw_map = {
                    'jacuzzi': ['jacuzzi', 'tina', 'hidromasaje'],
                    'piscina': ['piscina', 'alberca', 'pileta'],
                    'sauna': ['sauna', 'turco', 'baño turco'],
                    'hogar': ['hogar', 'ducha', 'residencial', 'doméstico', 'bano'],
                }
                keywords = kw_map.get(use_case, [])
                if keywords:
                    q = Q()
                    for kw in keywords:
                        q |= Q(name__icontains=kw) | Q(description__icontains=kw)
                    use_filtered = products.filter(q)
                    if use_filtered.exists():
                        products = use_filtered

            products_list = list(products.order_by('category__name', 'price')[:40])

            if not products_list:
                lines.append('CATÁLOGO: no hay productos disponibles para esa categoría o uso.')
            else:
                lines.append('CATÁLOGO DE PRODUCTOS (recomienda solo de esta lista):')
                for p in products_list:
                    price = '${:,.0f}'.format(float(p.price))
                    availability = 'en stock' if p.total_stock > 0 else 'sin stock disponible'
                    description = (getattr(p, 'description', '') or '').strip()
                    desc_snippet = (' | ' + description[:120]) if description else ''
                    specs = ', '.join(
                        f'{item.attribute.name}: {item.value}{(" " + item.attribute.unit) if item.attribute.unit else ""}'
                        for item in p.specifications.all()
                    )
                    specs_text = f' | {specs}' if specs else ''
                    lines.append(
                        f'{p.name} | {p.category.name} | {p.brand.name} | {price} | {availability}'
                        f' | {self._product_url(p.id, channel)}{desc_snippet}{specs_text}'
                    )

            return '\n'.join(lines)
        except Exception:
            logger.exception('No fue posible construir el contexto CRM para Ollama')
            return self.CONTEXT_FALLBACK

    def _catalog_has_product(self, requested_product, category_filter=None):
        if not requested_product:
            return True
        try:
            from django.db.models import Q
            from ecommerce.models import Product

            products = Product.objects.filter(is_available=True)
            if category_filter and products.filter(
                Q(category__name__iexact=category_filter) |
                Q(category__parent__name__iexact=category_filter)
            ).exists():
                return True

            stop_words = {'para', 'con', 'del', 'gas', 'agua', 'los', 'las', 'que', 'una', 'uno'}
            requested_tokens = [
                token for token in self._normalize(requested_product).split()
                if len(token) > 2 and token not in stop_words
            ]
            if not requested_tokens:
                return False

            q = Q()
            for token in requested_tokens:
                q |= (
                    Q(name__icontains=token) | Q(description__icontains=token) |
                    Q(category__name__icontains=token) | Q(category__description__icontains=token) |
                    Q(brand__name__icontains=token) |
                    Q(specifications__attribute__name__icontains=token) |
                    Q(specifications__value__icontains=token)
                )
            return products.filter(q).exists()
        except Exception:
            logger.exception('No fue posible validar el producto contra el catálogo')
            return False

    @staticmethod
    def _product_search_text(product):
        category_path = [product.category.name, product.category.description or '']
        if product.category.parent:
            category_path.extend([product.category.parent.name, product.category.parent.description or ''])
        specs = []
        for spec in product.specifications.all():
            specs.extend([spec.attribute.name, spec.attribute.description or '', str(spec.value), spec.attribute.unit or ''])
        return ' '.join([
            product.name, product.description or '', product.brand.name,
            *category_path, *specs,
        ])

    @staticmethod
    def _product_url(product_id, channel='ecommerce'):
        template = (
            settings.PRODUCT_URL_TEMPLATE
            if channel == 'ecommerce'
            else settings.EXTERNAL_PRODUCT_URL_TEMPLATE
        )
        return template.format(id=product_id)

    def _product_link(self, product_id, channel='ecommerce'):
        url = self._product_url(product_id, channel)
        if channel == 'ecommerce':
            return f'[Ver producto →]({url})'
        return f'Ver producto → {url}'

    def _get_recommendations(self, category_filter, requested_product, budget=None, use_case=None, preferences=None):
        """Ordena productos reales por compatibilidad con todo el catálogo publicado."""
        try:
            from ecommerce.models import Product

            products = list(Product.objects.filter(
                is_available=True, total_stock__gt=0,
            ).select_related('category', 'category__parent', 'brand').prefetch_related(
                'specifications__attribute',
            ))
            preferences = preferences or {}
            query = self._normalize(' '.join(filter(None, [
                requested_product, use_case, preferences.get('model_preference'),
                preferences.get('gas_type'), preferences.get('heater_type'),
            ])))
            query_tokens = {token for token in re.findall(r'[a-z0-9]+', query) if len(token) > 2}
            requirements = preferences.get('requirements') or {}
            if preferences.get('intent') == 'replacement_part':
                part_terms = ('repuesto', 'recambio', 'pieza', 'accesorio', 'valvula', 'manguera', 'regulador')
                products = [product for product in products if any(
                    term in self._normalize(self._product_search_text(product)) for term in part_terms
                )]
            use_has_match = bool(use_case) and any(
                self._normalize(use_case) in self._normalize(self._product_search_text(product))
                for product in products
            )
            bathrooms = preferences.get('bathrooms')
            def matches_bathrooms(product):
                if not bathrooms:
                    return False
                for spec in product.specifications.all():
                    attribute = self._normalize(spec.attribute.name)
                    value = self._normalize(str(spec.value))
                    if ('bano' in attribute or 'ducha' in attribute) and re.search(rf'\b{bathrooms}\b', value):
                        return True
                text = self._normalize(self._product_search_text(product))
                return bool(re.search(rf'\b{bathrooms}\s*(?:banos?|duchas?)\b', text))

            bathrooms_have_match = bool(bathrooms) and any(matches_bathrooms(product) for product in products)
            similar_product = None
            if preferences.get('similar_to_product_id'):
                similar_product = next(
                    (product for product in products if product.id == preferences['similar_to_product_id']), None,
                )
            exact_product_id = preferences.get('selected_product_id') if not similar_product else None
            ranked = []
            for product in products:
                if exact_product_id and product.id != exact_product_id:
                    continue
                text = self._normalize(self._product_search_text(product))
                category_names = [product.category.name]
                if product.category.parent:
                    category_names.append(product.category.parent.name)
                if category_filter and not any(
                    self._normalize(name) == self._normalize(category_filter) for name in category_names
                ):
                    continue
                brand = preferences.get('brand_preference')
                if brand and brand != 'any' and self._normalize(product.brand.name) != self._normalize(brand):
                    continue

                product_specs = {
                    self._normalize(spec.attribute.name): self._normalize(str(spec.value))
                    for spec in product.specifications.all()
                }
                if any(
                    product_specs.get(self._normalize(name)) != self._normalize(str(value))
                    for name, value in requirements.items()
                ):
                    continue
                hard_values = []
                if preferences.get('capacity'):
                    hard_values.append(str(preferences['capacity']))
                if preferences.get('gas_type'):
                    hard_values.append(str(preferences['gas_type']))
                if preferences.get('heater_type'):
                    hard_values.append(str(preferences['heater_type']))
                if any(self._normalize(value) not in text for value in hard_values):
                    continue
                if use_has_match and self._normalize(use_case) not in text:
                    continue
                if bathrooms_have_match and not matches_bathrooms(product):
                    continue
                if similar_product and product.id == similar_product.id:
                    continue

                score = 20 if category_filter else 0
                matched = sorted(token for token in query_tokens if token in text)
                score += len(matched) * 4
                score += len(requirements) * 12
                reasons = []
                if category_filter:
                    reasons.append(f'categoría {category_filter}')
                if requirements:
                    reasons.extend(f'{name}: {value}' for name, value in requirements.items())
                if use_case and self._normalize(use_case) in text:
                    reasons.append(f'uso {use_case}')
                    score += 8
                if brand and brand != 'any':
                    reasons.append(f'marca {product.brand.name}')
                if bathrooms and bathrooms_have_match:
                    reasons.append(f'{bathrooms} baños simultáneos')
                    score += 10
                if similar_product:
                    if product.category_id == similar_product.category_id:
                        score += 12
                        reasons.append(f'similar a {similar_product.name}')
                    if product.brand_id == similar_product.brand_id:
                        score += 3
                    similar_specs = {
                        (self._normalize(spec.attribute.name), self._normalize(str(spec.value)))
                        for spec in similar_product.specifications.all()
                    }
                    product_spec_pairs = {
                        (self._normalize(spec.attribute.name), self._normalize(str(spec.value)))
                        for spec in product.specifications.all()
                    }
                    score += len(similar_specs & product_spec_pairs) * 3
                for restriction in preferences.get('restrictions') or []:
                    if self._normalize(restriction) in text:
                        score += 3
                if matched:
                    reasons.append('coincide con ' + ', '.join(matched[:3]))
                product._compatibility_score = score
                product._compatibility_reasons = reasons[:3]
                ranked.append(product)

            ranked.sort(key=lambda item: (-item._compatibility_score, float(item.price), item.name))
            if budget:
                within = [p for p in ranked if float(p.price) <= budget]
                above = [p for p in ranked if float(p.price) > budget]
                return within[:3] if within else above[:3], above[:2] if within else []
            return ranked[:3], []
        except Exception:
            logger.exception('No fue posible obtener recomendaciones del catálogo')
            return [], []

    def _heater_qualification_question(self, state):
        """Devuelve solamente la siguiente pregunta faltante para calentadores."""
        category = self._normalize(state.get('category') or '')
        product = self._normalize(state.get('product') or '')
        if 'calentador' not in category and 'calentador' not in product:
            return None
        if state.get('selected_product_id'):
            return None

        from ecommerce.models import Brand, Product

        questions = []
        if not state.get('use_case'):
            questions.append((
                'use_case', 'tipo de uso', ['Baño convencional', 'Jacuzzi', 'Sauna', 'Piscina', 'Otro uso'],
                'Para ayudarte a elegir la mejor opción, ¿lo necesitas para un baño convencional, jacuzzi, sauna o piscina?',
            ))
        if not state.get('bathrooms'):
            questions.append((
                'bathrooms', 'duchas o puntos de agua simultáneos', [],
                '¿Cuántas duchas o puntos de agua se utilizarían al mismo tiempo?',
            ))
        if not state.get('property_type'):
            questions.append((
                'property_type', 'tipo de inmueble', ['Casa', 'Apartamento', 'Negocio', 'Otro'],
                '¿Es para una casa, apartamento, negocio u otro espacio?',
            ))
        if not state.get('gas_type'):
            questions.append((
                'gas_type', 'fuente de energía', ['Gas natural', 'GLP', 'Electricidad'],
                '¿Utilizas gas natural, GLP o electricidad?',
            ))
        if not state.get('heater_type'):
            questions.append((
                'heater_type', 'tipo de calentador', ['Paso', 'Acumulación', 'Solar'],
                '¿Buscas calentador de paso, acumulación o solar?',
            ))
        if not state.get('brand_preference'):
            category_products = Product.objects.filter(is_available=True)
            if state.get('category'):
                category_products = category_products.filter(category__name__iexact=state['category'])
            brand_ids = category_products.values_list('brand_id', flat=True).distinct()
            brands = list(Brand.objects.filter(pk__in=brand_ids, is_active=True).order_by('name').values_list('name', flat=True)[:6])
            questions.append((
                'brand_preference', 'marca preferida', [*brands, 'Sin preferencia'],
                '¿Tienes alguna marca o modelo preferido? Puedes responder “sin preferencia”.',
            ))
        if not state.get('restrictions'):
            questions.append((
                'restrictions', 'limitaciones de espacio o instalación', [],
                '¿Tienes alguna limitación de espacio o instalación? Si no tienes, responde “ninguna”.',
            ))
        if not questions:
            return None

        key, label, options, question = questions[0]
        state['pending_question'] = {'key': key, 'label': label, 'options': options}
        state['stage'] = 'qualification'
        asked = list(state.get('asked_attributes') or [])
        if label not in asked:
            asked.append(label)
        state['asked_attributes'] = asked
        return question

    def _next_catalog_question(self, products, state):
        """Elige un atributo real que ayude a distinguir las opciones restantes."""
        asked = {self._normalize(item) for item in (state.get('asked_attributes') or [])}
        known = {self._normalize(item) for item in (state.get('requirements') or {})}
        options = {}
        labels = {}
        orders = {}
        for product in products:
            for spec in product.specifications.all():
                key = self._normalize(spec.attribute.name)
                options.setdefault(key, set()).add(str(spec.value))
                labels[key] = spec.attribute.name
                orders[key] = spec.attribute.order
        def already_known(key):
            semantic_fields = (
                (state.get('bathrooms'), ('bano', 'ducha')),
                (state.get('gas_type'), ('gas', 'combustible', 'energia')),
                (state.get('heater_type'), ('tipo', 'tecnologia')),
                (state.get('capacity'), ('capacidad', 'litro', 'caudal')),
                (state.get('brand_preference'), ('marca',)),
                (state.get('model_preference'), ('modelo', 'referencia')),
                (state.get('use_case'), ('uso', 'aplicacion')),
            )
            return key in known or any(value and any(word in key for word in words) for value, words in semantic_fields)

        candidates = [
            key for key, values in options.items()
            if len(values) > 1 and key not in asked and not already_known(key)
        ]
        if not candidates:
            return None
        priority_words = ('uso', 'bano', 'capacidad', 'gas', 'tipo', 'modelo', 'instalacion', 'marca')
        candidates.sort(key=lambda key: (
            next((i for i, word in enumerate(priority_words) if word in key), len(priority_words)),
            orders.get(key, 999),
            -len(options[key]),
        ))
        selected = candidates[0]
        state['asked_attributes'] = list(state.get('asked_attributes') or []) + [labels[selected]]
        sorted_options = sorted(options[selected], key=self._normalize)[:6]
        state['pending_question'] = {
            'key': 'requirements',
            'attribute': labels[selected],
            'label': labels[selected],
            'options': sorted_options,
        }
        choices = ', '.join(sorted_options)
        return f'Para recomendarte la opción más compatible, ¿qué {labels[selected].lower()} necesitas? Opciones disponibles: {choices}.'

    def _format_recommendations(self, products, budget=None, channel='ecommerce'):
        """Formatea hasta tres productos reales y explica por qué coinciden."""
        parts = []
        for p in products:
            availability = 'en stock' if p.total_stock > 0 else 'sin stock disponible'
            budget_note = ' (fuera de presupuesto)' if budget and float(p.price) > budget else ''
            desc = ''  # La ficha enlazada muestra la descripción completa sin cortes.
            lines = [
                f'**{p.name}**',
                f'Marca: {p.brand.name} | Precio: ${float(p.price):,.0f} | {availability}{budget_note}',
            ]
            specs = list(p.specifications.all())[:5]
            if specs:
                lines.append('Características: ' + ', '.join(
                    f'{spec.attribute.name}: {spec.value}{(" " + spec.attribute.unit) if spec.attribute.unit else ""}'
                    for spec in specs
                ))
            reasons = getattr(p, '_compatibility_reasons', [])
            if reasons:
                lines.append('Por qué coincide: ' + '; '.join(reasons))
            if desc:
                lines.append(desc[:100])
            lines.append(self._product_link(p.id, channel))
            parts.append('\n'.join(lines))
        return '\n\n'.join(parts)

    @staticmethod
    def _result(response, state, summary):
        return {
            'response': response,
            'needs_agent': False,
            'state': state,
            'summary': summary,
            'error': None,
        }

    def add_initial_greeting(self, response):
        response = (response or '').strip()
        if self.INITIAL_GREETING.lower() in response.lower():
            return response
        return f'{self.INITIAL_GREETING}\n\n{response}' if response else self.INITIAL_GREETING

    def get_bot_response(self, message, conversation_history=None, conversation_state=None, summary='', channel='ecommerce'):
        state = self.update_state(message, conversation_state)
        state_summary = self.summarize_state(state)

        referenced, reference_ambiguous = self._resolve_reference_product(
            message, state, conversation_history,
        )
        if referenced:
            state.update(
                product=referenced.name,
                category=referenced.category.name,
                selected_product_id=referenced.id,
            )
            state_summary = self.summarize_state(state)

        if state.get('intent') in ('price', 'availability') and referenced:
            availability = 'disponible' if referenced.is_available and referenced.total_stock > 0 else 'sin stock disponible'
            response = (
                f'**{referenced.name}** cuesta ${float(referenced.price):,.0f} y está {availability}.\n'
                f'{self._product_link(referenced.id, channel)}'
            )
            return self._result(response, state, state_summary)
        if state.get('intent') in ('price', 'availability') and reference_ambiguous:
            return self._result(
                '¿A cuál de los productos mostrados te refieres? Indica el nombre o la posición.',
                state, state_summary,
            )
        normalized_message = self._normalize(message).strip(' .!?')
        if referenced and re.fullmatch(
            r'(?:ese|esa|este|esta|el primero|el segundo|el tercero|ese modelo|el que me mostraste|me interesa)',
            normalized_message,
        ):
            state['recent_products'] = self._product_context([referenced])
            return self._result(
                f'Te refieres a:\n\n{self._format_recommendations([referenced], channel=channel)}\n\n'
                '¿Quieres conocer el precio, la disponibilidad o continuar la compra?',
                state, self.summarize_state(state),
            )

        if self._purchase_requested(message) and not self._is_out_of_scope(message):
            selected, ambiguous = self._resolve_purchase(message, state, conversation_history)
            if selected:
                state.update(product=selected.name, category=selected.category.name, selected_product_id=selected.id)
                if not selected.is_available or selected.total_stock <= 0:
                    state.update(needs_human=False, stage='recommendation')
                    return self._result(f'Actualmente **{selected.name}** no tiene stock disponible.', state, self.summarize_state(state))
                state.update(intent='purchase', needs_human=True, stage='human_handoff', topic='human_support')
                return {'response': f'Has seleccionado **{selected.name}**. {self._product_link(selected.id, channel)}\n\nVoy a comunicarte con un asesor para continuar la compra.',
                        'needs_agent': True, 'state': state, 'summary': self.summarize_state(state), 'error': None}
            if state.get('needs_human'):
                return {
                    'response': 'Entendido. Voy a comunicarte con un asesor humano para continuar con tu solicitud comercial.',
                    'needs_agent': True,
                    'state': state,
                    'summary': state_summary,
                    'error': None,
                }
            if ambiguous is not None:
                state.update(needs_human=False, stage='recommendation')
                return self._result('¿Cuál de los productos mostrados quieres comprar? Indica su nombre o posición.' if ambiguous
                                    else 'No encontré el producto solicitado en el catálogo actual. ¿Puedes indicar su nombre?',
                                    state, self.summarize_state(state))

        if state['needs_human']:
            return {
                'response': 'Claro. Voy a comunicarte con un asesor humano para que continúe ayudándote.',
                'needs_agent': True,
                'state': state,
                'summary': state_summary,
                'error': None,
            }

        if state.get('topic') == 'greeting' and not state.get('product') and not state.get('category'):
            if channel == 'ecommerce' and state.get('greeting_shown'):
                return self._result(
                    '¿Cómo puedo ayudarte con nuestros productos o servicios?',
                    state, state_summary,
                )
            return self._result(self.INITIAL_GREETING, state, state_summary)

        # Solicitud fuera del alcance de la empresa
        if self._is_out_of_scope(message):
            return self._result(
                'Estoy aquí para ayudarte con información sobre los productos y servicios de '
                'IMPORGAS JJ. ¿Qué producto estás buscando?',
                state,
                state_summary,
            )

        product = state.get('product')
        category_filter = state.get('category') or self._detect_category_filter(product or '')
        use_case = state.get('use_case')
        budget = state.get('budget')

        # Envíos
        if state.get('topic') == 'shipping':
            product_in_catalog = self._catalog_has_product(product, category_filter)
            suffix = (
                f' Sin embargo, no encontré "{product}" en el catálogo actual.'
                if product and not product_in_catalog else ''
            )
            return self._result(
                'No tengo información confirmada sobre las condiciones de entrega en este momento. '
                'Puedo pasar tu consulta a uno de nuestros asesores para que te ayude.' + suffix,
                state, state_summary,
            )

        # Garantía
        if state.get('topic') == 'warranty':
            return self._result(
                'No tengo información confirmada sobre la garantía de ese producto en este momento. '
                'Puedo pasar tu consulta a uno de nuestros asesores para que te ayude.',
                state, state_summary,
            )

        if state.get('intent') == 'replacement_part' and not (product or category_filter):
            from ecommerce.models import Category

            options = list(Category.objects.filter(is_active=True).order_by('name').values_list('name', flat=True)[:6])
            state['pending_question'] = {
                'key': 'category', 'label': 'equipo o categoría', 'options': options,
            }
            state['stage'] = 'qualification'
            choices = ', '.join(options) if options else 'el equipo al que pertenece'
            return self._result(
                f'¿Para qué equipo necesitas el repuesto? Puedes indicar una de estas categorías: {choices}.',
                state, self.summarize_state(state),
            )

        pending = state.get('pending_question') or {}
        if pending and not self._answer_pending_question(message, state):
            label = pending.get('label') or pending.get('attribute') or 'dato solicitado'
            options = pending.get('options') or []
            suffix = f" Opciones disponibles: {', '.join(map(str, options))}." if options else ''
            return self._result(
                f'Necesito que me indiques {label} para continuar.{suffix}',
                state, self.summarize_state(state),
            )

        if state.get('intent') in ('recommendation', 'purchase', 'compatibility'):
            question = self._heater_qualification_question(state)
            if question:
                return self._result(question, state, self.summarize_state(state))

        # Producto o categoría detectada → consultar y puntuar únicamente el catálogo real.
        if state.get('intent') in ('purchase', 'recommendation', 'replacement_part', 'compatibility', 'price', 'availability') and (product or category_filter):
            # Validar que el producto exista en catálogo
            if product and not category_filter:
                if not self._catalog_has_product(product, None):
                    return self._result(
                        f'No encontré "{product}" en nuestro catálogo actual. '
                        'Trabajamos con calentadores de agua (hogar, jacuzzi, piscina), '
                        'reguladores de gas y accesorios. ¿Puedes describirme mejor lo que necesitas?',
                        state, state_summary,
                    )

            recommended, above_budget = self._get_recommendations(
                category_filter, product, budget, use_case, preferences=state,
            )

            product_label = category_filter or product or 'el producto solicitado'
            if use_case:
                use_labels = {'jacuzzi': 'jacuzzi', 'piscina': 'piscina', 'sauna': 'sauna', 'hogar': 'uso en hogar'}
                product_label = f'{product_label} para {use_labels.get(use_case, use_case)}'

            if recommended:
                if len(recommended) > 1 and state.get('intent') in ('recommendation', 'replacement_part', 'compatibility'):
                    question = self._next_catalog_question(recommended, state)
                    if question:
                        state['stage'] = 'qualification'
                        return self._result(question, state, self.summarize_state(state))
                state['recent_products'] = self._product_context(recommended)
                state['selected_product_id'] = None
                if budget:
                    header = f'Para tu presupuesto de ${budget:,.0f}, estas son las opciones disponibles:'
                else:
                    header = f'Estas son las opciones disponibles de {product_label}:'
                options_text = self._format_recommendations(recommended, channel=channel)

                footer = ''
                if above_budget:
                    extra_text = self._format_recommendations(above_budget, budget=budget, channel=channel)
                    footer = (
                        f'\n\nTambién hay opciones fuera de ese presupuesto:\n\n{extra_text}'
                    )

                return self._result(
                    f'{header}\n\n{options_text}{footer}\n\n'
                    f'¿Te gustaría más información sobre alguno de estos modelos?',
                    state, state_summary,
                )

            return self._result(
                f'En este momento no encontré {product_label} disponibles en nuestro catálogo. '
                '¿Puedo ayudarte con algo más o prefieres que un asesor te contacte?',
                state, state_summary,
            )

        # Para el resto de consultas, usar Ollama con el contexto del catálogo
        messages = [
            {'role': 'system', 'content': self.SYSTEM_PROMPT},
            {'role': 'system', 'content': self._build_company_context(category_filter, use_case, channel)},
            {'role': 'system', 'content': 'ESTADO ACTUAL: ' + json.dumps(state, ensure_ascii=False)},
        ]
        if summary:
            messages.append({'role': 'system', 'content': 'RESUMEN PERSISTENTE: ' + str(summary)[:3000]})
        for item in (conversation_history or [])[-12:]:
            role = 'assistant' if item.get('role') in ('bot', 'assistant', 'agent') else 'user'
            content = str(item.get('content', '')).strip()
            if content:
                messages.append({'role': role, 'content': content[:2000]})
        messages.append({'role': 'user', 'content': message})

        payload = {
            'model': self.model,
            'messages': messages,
            'stream': False,
            'options': {
                'temperature': 0.1,
                'num_predict': 450,
                'num_ctx': self.num_ctx,
            },
        }
        lock_key = 'crm-chat:ollama:request-lock'
        lock_token = str(uuid.uuid4())
        wait_until = time.monotonic() + max(0, settings.OLLAMA_QUEUE_WAIT)
        acquired = cache.add(lock_key, lock_token, timeout=self.timeout + settings.OLLAMA_QUEUE_WAIT + 10)
        while not acquired and time.monotonic() < wait_until:
            time.sleep(0.2)
            acquired = cache.add(lock_key, lock_token, timeout=self.timeout + settings.OLLAMA_QUEUE_WAIT + 10)
        if not acquired:
            logger.warning('Ollama ocupado: se agotó la espera de la cola local.')
            return {
                'response': 'El asesor comercial virtual está atendiendo otra consulta. Inténtalo nuevamente en unos segundos.',
                'needs_agent': False,
                'state': state,
                'summary': state_summary,
                'error': 'queue_timeout',
            }
        try:
            logger.info('Petición a Ollama: modelo=%s mensajes=%s', self.model, len(messages))
            response = requests.post(self.api_url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            bot_message = response.json().get('message', {}).get('content', '').strip()
            if not bot_message:
                bot_message = 'No pude procesar esa pregunta. ¿Puedes reformularla brevemente?'
            unsafe_identity = re.search(r'\b(?:chatgpt|ollama|openai|soy una (?:ia|inteligencia artificial))\b', self._normalize(bot_message))
            internal_url = re.search(r'https?://(?:localhost|127\.0\.0\.1|backend|frontend|nginx)(?::\d+)?', bot_message, re.I)
            if unsafe_identity or internal_url:
                logger.warning('Ollama devolvió contenido no permitido; se aplicó respuesta segura.')
                bot_message = 'Soy el asesor comercial virtual de IMPORGAS JJ. ¿Qué producto o servicio necesitas?'
            return {
                'response': bot_message,
                'needs_agent': False,
                'state': state,
                'summary': state_summary,
                'error': None,
            }
        except requests.exceptions.Timeout:
            logger.warning('Ollama excedió el timeout configurado')
            return {
                'response': 'El asesor comercial virtual está tardando más de lo esperado. Puedes intentarlo de nuevo.',
                'needs_agent': False,
                'state': state,
                'summary': state_summary,
                'error': 'timeout',
            }
        except requests.exceptions.ConnectionError:
            logger.warning('No fue posible conectar con Ollama')
            return {
                'response': 'El asesor comercial virtual no está disponible temporalmente. Puedes intentarlo de nuevo.',
                'needs_agent': False,
                'state': state,
                'summary': state_summary,
                'error': 'connection_error',
            }
        except (requests.RequestException, ValueError, TypeError):
            logger.exception('Respuesta inválida de Ollama')
            return {
                'response': 'No pude procesar tu mensaje en este momento. Inténtalo nuevamente.',
                'needs_agent': False,
                'state': state,
                'summary': state_summary,
                'error': 'ollama_error',
            }
        finally:
            if cache.get(lock_key) == lock_token:
                cache.delete(lock_key)


ollama_service = OllamaService()
