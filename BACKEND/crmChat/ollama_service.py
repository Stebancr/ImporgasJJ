"""Integración de Ollama con memoria estructurada para el CRM de gasodomésticos."""
import json
import logging
import re
import unicodedata
from difflib import get_close_matches

import requests
from django.conf import settings


logger = logging.getLogger(__name__)


class OllamaService:
    INITIAL_GREETING = (
        'Hola, gracias por comunicarte con IMPORGAS JJ. Soy tu asesor comercial virtual. '
        '¿En qué puedo ayudarte el día de hoy?'
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
            'budget': None,
            'stage': 'discovery',
            'topic': None,
            'previous_topics': [],
            'requirements': {},
            'asked_attributes': [],
            'needs_human': False,
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
        if any(term in normalized for term in ('ducha', 'bano', 'hogar', 'casa', 'apartamento', 'lavamanos', 'residencial')):
            return 'hogar'
        return None

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

    def update_state(self, message, current_state=None):
        state = self.default_state()
        state.update(current_state or {})
        state['previous_topics'] = list(state.get('previous_topics') or [])[-4:]
        normalized = self._normalize(message)

        handoff = bool(state.get('needs_human')) or self.needs_human_agent(message)

        if any(word in normalized for word in self.PURCHASE_WORDS):
            state['intent'] = 'purchase'

        category = self._detect_category_filter(message)
        use_case = self._detect_use_case(message)
        product = self._extract_product(message)

        # El bot orienta por producto y especificaciones, no solicita ni conserva presupuesto.
        state['budget'] = None

        if category:
            state['category'] = category
            state['intent'] = state.get('intent') or 'purchase'
        if use_case:
            state['use_case'] = use_case
        if product:
            state['product'] = product
            state['intent'] = state.get('intent') or 'purchase'
        if re.search(r'\b(?:repuesto|recambio|pieza|accesorio)\b', normalized):
            state['intent'] = 'replacement_part'

        if any(phrase in normalized for phrase in (
            'cualquier marca', 'sin preferencia de marca', 'me da igual la marca', 'no importa la marca',
        )):
            state['brand_preference'] = 'any'

        if category and category != (current_state or {}).get('category'):
            for key in ('brand_preference', 'capacity', 'gas_type', 'heater_type', 'use_case'):
                state[key] = None
            state['requirements'] = {}
            state['asked_attributes'] = []
            state['use_case'] = use_case
        capacity = re.search(r'\b(\d{1,3})\s*(?:litros?|lts?|l)\b', normalized)
        if not capacity and ('calentador' in normalized or 'paso' in normalized):
            capacity = re.search(r'\b(\d{1,2})\s*$', normalized)
        if capacity:
            state['capacity'] = int(capacity.group(1))
        for gas in ('natural', 'propano', 'glp'):
            if re.search(r'\b' + gas + r'\b', normalized):
                state['gas_type'] = gas
        if 'paso' in normalized:
            state['heater_type'] = 'paso'
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
        except Exception:
            logger.exception('No fue posible identificar especificaciones del catálogo')

        topic = state.get('topic')
        if any(word in normalized for word in ('envio', 'domicilio', 'entrega', 'despacho', 'delivery')):
            new_topic = 'shipping'
        elif any(word in normalized for word in ('garantia', 'devolucion', 'cambio')):
            new_topic = 'warranty'
        elif any(word in normalized for word in ('instalacion', 'reparacion', 'mantenimiento', 'tecnico')):
            new_topic = 'technical_service'
        elif state.get('product') or state.get('category'):
            new_topic = 'product'
        elif any(word in normalized for word in ('hola', 'buenas', 'buenos dias', 'buenas tardes', 'buenas noches')):
            new_topic = 'greeting'
        else:
            new_topic = topic

        if topic and new_topic and new_topic != topic:
            state['previous_topics'] = (state['previous_topics'] + [topic])[-4:]
        state['topic'] = new_topic

        if state.get('intent') == 'purchase':
            state['stage'] = 'recommendation' if (state.get('product') or state.get('category')) else 'discovery'
        elif new_topic == 'greeting':
            state['stage'] = 'greeting'
        state['needs_human'] = handoff
        if handoff:
            state.update(stage='human_handoff', topic='human_support')
        return state

    @staticmethod
    def summarize_state(state):
        parts = []
        labels = (
            ('intent', 'intención'), ('product', 'producto'), ('category', 'categoría'),
            ('use_case', 'uso'), ('stage', 'etapa'), ('topic', 'tema'),
        )
        for key, label in labels:
            value = state.get(key)
            if value not in (None, '', []):
                parts.append(f'{label}: {value}')
        parts.append(f"requiere humano: {'sí' if state.get('needs_human') else 'no'}")
        return '; '.join(parts)

    def _build_company_context(self, category_filter=None, use_case=None):
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
                        f' | {self._product_url(p.id)}{desc_snippet}{specs_text}'
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
    def _product_url(product_id):
        return settings.PRODUCT_URL_TEMPLATE.format(id=product_id)

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
            query = self._normalize(' '.join(filter(None, [requested_product, use_case])))
            query_tokens = {token for token in re.findall(r'[a-z0-9]+', query) if len(token) > 2}
            requirements = preferences.get('requirements') or {}
            ranked = []
            for product in products:
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
                if matched and not reasons:
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
        candidates = [key for key, values in options.items() if len(values) > 1 and key not in asked and key not in known]
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
        choices = ', '.join(sorted(options[selected], key=self._normalize)[:6])
        return f'Para recomendarte la opción más compatible, ¿qué {labels[selected].lower()} necesitas? Opciones disponibles: {choices}.'

    def _format_recommendations(self, products, budget=None):
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
            lines.append(self._product_url(p.id))
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

    def get_bot_response(self, message, conversation_history=None, conversation_state=None, summary=''):
        state = self.update_state(message, conversation_state)
        state_summary = self.summarize_state(state)

        if self._purchase_requested(message) and not self._is_out_of_scope(message):
            selected, ambiguous = self._resolve_purchase(message, state, conversation_history)
            if selected:
                state.update(product=selected.name, category=selected.category.name, selected_product_id=selected.id)
                if not selected.is_available or selected.total_stock <= 0:
                    state.update(needs_human=False, stage='recommendation')
                    return self._result(f'Actualmente **{selected.name}** no tiene stock disponible.', state, self.summarize_state(state))
                state.update(intent='purchase', needs_human=True, stage='human_handoff', topic='human_support')
                return {'response': f'Has seleccionado **{selected.name}**. {self._product_url(selected.id)}\n\nVoy a comunicarte con un asesor para continuar la compra.',
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

        # Producto o categoría detectada → mostrar recomendaciones directamente desde la BD
        if state.get('intent') in ('purchase', 'replacement_part') and (product or category_filter):
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
                category_filter, product, None, use_case, preferences=state,
            )

            product_label = category_filter or product or 'el producto solicitado'
            if use_case:
                use_labels = {'jacuzzi': 'jacuzzi', 'piscina': 'piscina', 'hogar': 'uso en hogar'}
                product_label = f'{product_label} para {use_labels.get(use_case, use_case)}'

            if recommended:
                if len(recommended) > 1 and re.search(r'\b(?:recomiend|recomendacion|cual me sirve|cual necesito)\w*\b', self._normalize(message)):
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
                options_text = self._format_recommendations(recommended)

                footer = ''
                if above_budget:
                    extra_text = self._format_recommendations(above_budget, budget=budget)
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
            {'role': 'system', 'content': self._build_company_context(category_filter, use_case)},
            {'role': 'system', 'content': 'ESTADO ACTUAL: ' + json.dumps(state, ensure_ascii=False)},
        ]
        for item in (conversation_history or [])[-8:]:
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
        try:
            logger.info('Petición a Ollama: modelo=%s mensajes=%s', self.model, len(messages))
            response = requests.post(self.api_url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            bot_message = response.json().get('message', {}).get('content', '').strip()
            if not bot_message:
                bot_message = 'No pude procesar esa pregunta. ¿Puedes reformularla brevemente?'
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


ollama_service = OllamaService()
