-- =============================================================
--  ESQUEMA PostgreSQL — 3FN optimizado
--  Compatible con: PostgreSQL 14+
--
--  Cambios respecto a versión anterior:
--    · spec_attributes: catálogo normalizado de atributos de especificación
--      → product_specs.key (TEXT libre) reemplazado por FK a spec_attributes
--    · products.discount eliminado — es dato derivado de price/original_price
--    · unique_together → UNIQUE CONSTRAINT con nombre
--    · CheckConstraints en todas las tablas con reglas de negocio
--    · Índice parcial para productos destacados (is_featured = TRUE)
--    · Columna search_vector (TSVECTOR) + índice GIN para búsqueda full-text
--    · Trigger actualiza search_vector automáticamente
--    · Trigger recalcula products.rating / reviews_count en cada cambio de reseña
-- =============================================================

-- ───────────────────────────────────────────
--  USERS
-- ───────────────────────────────────────────
CREATE TABLE users (
    id         BIGSERIAL    PRIMARY KEY,
    email      VARCHAR(254) NOT NULL UNIQUE,
    name       VARCHAR(150) NOT NULL,
    phone      VARCHAR(20)  NOT NULL DEFAULT '',
    address    TEXT         NOT NULL DEFAULT '',
    role       VARCHAR(10)  NOT NULL DEFAULT 'client'
                            CHECK (role IN ('admin', 'operator', 'client')),
    password   VARCHAR(128) NOT NULL,              -- hash gestionado por Django
    is_active  BOOLEAN      NOT NULL DEFAULT TRUE,
    is_staff   BOOLEAN      NOT NULL DEFAULT FALSE,
    is_superuser BOOLEAN    NOT NULL DEFAULT FALSE,
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ───────────────────────────────────────────
--  BRANDS
-- ───────────────────────────────────────────
CREATE TABLE brands (
    id          BIGSERIAL    PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    slug        VARCHAR(120) NOT NULL UNIQUE,
    logo        VARCHAR(500) NOT NULL DEFAULT '',   -- URL
    description TEXT         NOT NULL DEFAULT '',
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Marcas de ejemplo del frontend
INSERT INTO brands (name, slug, is_active) VALUES
    ('Haceb',     'haceb',     TRUE),
    ('Samsung',   'samsung',   TRUE),
    ('LG',        'lg',        TRUE),
    ('Fisher',    'fisher',    TRUE),
    ('Stanley',   'stanley',   TRUE),
    ('Bosch',     'bosch',     TRUE),
    ('Challenger','challenger',TRUE),
    ('Coltgas',   'coltgas',   TRUE);

-- ───────────────────────────────────────────
--  LOCATIONS  (puntos físicos / bodegas)
-- ───────────────────────────────────────────
CREATE TABLE locations (
    id         BIGSERIAL    PRIMARY KEY,
    name       VARCHAR(150) NOT NULL UNIQUE,
    address    TEXT         NOT NULL,
    city       VARCHAR(100) NOT NULL,
    phone      VARCHAR(20)  NOT NULL DEFAULT '',
    is_active  BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_locations_city ON locations (city);

-- ───────────────────────────────────────────
--  CATEGORIES
-- ───────────────────────────────────────────
CREATE TABLE categories (
    id          BIGSERIAL    PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    slug        VARCHAR(120) NOT NULL UNIQUE,
    icon        VARCHAR(100) NOT NULL DEFAULT '',   -- nombre del ícono
    description TEXT         NOT NULL DEFAULT '',
    parent_id   BIGINT       REFERENCES categories(id) ON DELETE SET NULL,
    "order"     SMALLINT     NOT NULL DEFAULT 0,
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Categorías raíz del frontend
INSERT INTO categories (name, slug, icon, "order") VALUES
    ('Calentadores',           'calentadores',  'flame',       1),
    ('Aires Acondicionados',   'aires',         'wind',        2),
    ('Reguladores de Gas',     'reguladores',   'gauge',       3),
    ('Herramientas e Instalación', 'herramientas', 'wrench',   4);

-- ───────────────────────────────────────────
--  SPEC ATTRIBUTES  (catálogo normalizado de atributos)
-- ───────────────────────────────────────────
-- Cada atributo existe UNA sola vez. Los productos referencian el mismo
-- registro via FK, eliminando duplicación y garantizando consistencia.
CREATE TABLE spec_attributes (
    id          BIGSERIAL    PRIMARY KEY,
    name        VARCHAR(150) NOT NULL UNIQUE,   -- ej: 'Capacidad'
    slug        VARCHAR(160) NOT NULL UNIQUE,   -- ej: 'capacidad'
    unit        VARCHAR(30)  NOT NULL DEFAULT '',  -- ej: 'Litros/min', 'kW'
    description TEXT         NOT NULL DEFAULT '',
    "order"     SMALLINT     NOT NULL DEFAULT 0
);

-- Atributos estándar del frontend (ProductDetailPage)
INSERT INTO spec_attributes (name, slug, unit, "order") VALUES
    ('Capacidad',    'capacidad',    'Litros/min', 1),
    ('Tipo de Gas',  'tipo-de-gas',  '',           2),
    ('Encendido',    'encendido',    '',           3),
    ('Tipo de Tiro', 'tipo-de-tiro', '',           4),
    ('Potencia',     'potencia',     'kW',         5),
    ('Dimensiones',  'dimensiones',  'cm',         6),
    ('Peso',         'peso',         'kg',         7),
    ('Garantía',     'garantia',     'años',       8),
    ('BTU',          'btu',          'BTU',        9),
    ('Voltaje',      'voltaje',      'V',         10);

-- ───────────────────────────────────────────
--  PRODUCTS
-- ───────────────────────────────────────────
CREATE TABLE products (
    id             BIGSERIAL      PRIMARY KEY,
    name           VARCHAR(255)   NOT NULL,
    slug           VARCHAR(280)   NOT NULL UNIQUE,
    description    TEXT           NOT NULL,
    -- discount NO se almacena: se calcula en la capa de aplicación como
    --   ROUND((1 - price / original_price) * 100)
    price          NUMERIC(12, 2) NOT NULL,
    original_price NUMERIC(12, 2),
    category_id    BIGINT         NOT NULL REFERENCES categories(id)  ON DELETE RESTRICT,
    brand_id       BIGINT         NOT NULL REFERENCES brands(id)      ON DELETE RESTRICT,
    -- stock por ubicación se gestiona en product_stock.
    -- total_stock es la suma de product_stock.quantity — actualizado por trigger.
    total_stock    INT            NOT NULL DEFAULT 0,
    is_available   BOOLEAN        NOT NULL DEFAULT TRUE,
    is_featured    BOOLEAN        NOT NULL DEFAULT FALSE,
    -- Desnormalizado — actualizado por trigger trg_review_rating
    rating         NUMERIC(3, 2)  NOT NULL DEFAULT 0.00,
    reviews_count  INT            NOT NULL DEFAULT 0,
    -- Full-text search (actualizado por trigger trg_product_search_vector)
    search_vector  TSVECTOR,
    created_at     TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ    NOT NULL DEFAULT NOW(),

    -- Reglas de negocio a nivel DB
    CONSTRAINT chk_product_price_positive          CHECK (price > 0),
    CONSTRAINT chk_product_total_stock_nonneg      CHECK (total_stock >= 0),
    CONSTRAINT chk_product_rating_range            CHECK (rating BETWEEN 0 AND 5),
    CONSTRAINT chk_product_original_price_gte_price
        CHECK (original_price IS NULL OR original_price >= price)
);

-- Índices compuestos para los filtros del ProductsPage
CREATE INDEX idx_products_cat_avail   ON products (category_id, is_available);
CREATE INDEX idx_products_brand_avail ON products (brand_id,    is_available);
CREATE INDEX idx_products_price       ON products (price);
CREATE INDEX idx_products_rating      ON products (rating DESC);
-- Índice parcial: solo registros destacados (evita leer toda la tabla)
CREATE INDEX idx_products_featured    ON products (is_featured) WHERE is_featured = TRUE;
-- Índice GIN para full-text search
CREATE INDEX idx_products_fts         ON products USING GIN (search_vector);

-- Trigger: mantiene search_vector actualizado con name + description
CREATE OR REPLACE FUNCTION update_product_search_vector()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('spanish', COALESCE(NEW.name, '')),        'A') ||
        setweight(to_tsvector('spanish', COALESCE(NEW.description, '')), 'B');
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_product_search_vector
BEFORE INSERT OR UPDATE OF name, description ON products
FOR EACH ROW EXECUTE FUNCTION update_product_search_vector();

-- ───────────────────────────────────────────
--  PRODUCT IMAGES
-- ───────────────────────────────────────────
CREATE TABLE product_images (
    id         BIGSERIAL    PRIMARY KEY,
    product_id BIGINT       NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    image      VARCHAR(500) NOT NULL,
    alt_text   VARCHAR(255) NOT NULL DEFAULT '',
    is_primary BOOLEAN      NOT NULL DEFAULT FALSE,
    "order"    SMALLINT     NOT NULL DEFAULT 0
);

CREATE INDEX idx_product_images_product ON product_images (product_id, "order");

-- Solo puede haber 1 imagen primaria por producto (índice parcial UNIQUE)
CREATE UNIQUE INDEX uniq_product_primary_image
    ON product_images (product_id)
    WHERE is_primary = TRUE;

-- ───────────────────────────────────────────
--  PRODUCT STOCK  (stock por punto físico)
-- ───────────────────────────────────────────
-- Un registro por combinación producto+ubicación.
-- UNIQUE(product_id, location_id) → imposible duplicar.
-- El trigger trg_product_total_stock mantiene products.total_stock actualizado.
CREATE TABLE product_stock (
    id          BIGSERIAL  PRIMARY KEY,
    product_id  BIGINT     NOT NULL REFERENCES products(id)  ON DELETE CASCADE,
    location_id BIGINT     NOT NULL REFERENCES locations(id) ON DELETE PROTECT,
    quantity    INT        NOT NULL DEFAULT 0,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uniq_product_stock_location UNIQUE (product_id, location_id),
    CONSTRAINT chk_product_stock_qty_nonneg CHECK (quantity >= 0)
);

CREATE INDEX idx_product_stock_product  ON product_stock (product_id);
CREATE INDEX idx_product_stock_location ON product_stock (location_id);

-- Trigger: recalcula products.total_stock al cambiar cualquier fila de product_stock
CREATE OR REPLACE FUNCTION update_product_total_stock()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    pid BIGINT := COALESCE(NEW.product_id, OLD.product_id);
BEGIN
    UPDATE products
    SET total_stock = COALESCE(
            (SELECT SUM(quantity) FROM product_stock WHERE product_id = pid), 0
        ),
        updated_at = NOW()
    WHERE id = pid;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_product_total_stock
AFTER INSERT OR UPDATE OR DELETE ON product_stock
FOR EACH ROW EXECUTE FUNCTION update_product_total_stock();

-- ───────────────────────────────────────────
--  PRODUCT SPECIFICATIONS
-- ───────────────────────────────────────────
-- attribute_id es FK a spec_attributes → el nombre del atributo nunca se duplica.
-- UNIQUE(product_id, attribute_id) → imposible repetir el mismo atributo en un producto.
CREATE TABLE product_specs (
    id           BIGSERIAL    PRIMARY KEY,
    product_id   BIGINT       NOT NULL REFERENCES products(id)        ON DELETE CASCADE,
    attribute_id BIGINT       NOT NULL REFERENCES spec_attributes(id) ON DELETE RESTRICT,
    value        VARCHAR(255) NOT NULL,
    "order"      SMALLINT     NOT NULL DEFAULT 0,
    CONSTRAINT uniq_product_spec_attribute UNIQUE (product_id, attribute_id)
);

CREATE INDEX idx_product_specs_product ON product_specs (product_id, "order");

-- ───────────────────────────────────────────
--  REVIEWS
-- ───────────────────────────────────────────
CREATE TABLE reviews (
    id         BIGSERIAL    PRIMARY KEY,
    product_id BIGINT       NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    user_id    BIGINT       NOT NULL REFERENCES users(id)    ON DELETE CASCADE,
    rating     SMALLINT     NOT NULL,
    title      VARCHAR(200) NOT NULL DEFAULT '',
    comment    TEXT         NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uniq_review_product_user UNIQUE (product_id, user_id),
    CONSTRAINT chk_review_rating_range  CHECK (rating BETWEEN 1 AND 5)
);

CREATE INDEX idx_reviews_product ON reviews (product_id);

-- Trigger: recalcula products.rating y products.reviews_count en cada cambio
CREATE OR REPLACE FUNCTION update_product_rating()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    pid BIGINT := COALESCE(NEW.product_id, OLD.product_id);
BEGIN
    UPDATE products
    SET
        rating        = COALESCE((SELECT ROUND(AVG(rating)::NUMERIC, 2) FROM reviews WHERE product_id = pid), 0),
        reviews_count = (SELECT COUNT(*) FROM reviews WHERE product_id = pid),
        updated_at    = NOW()
    WHERE id = pid;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_review_rating
AFTER INSERT OR UPDATE OR DELETE ON reviews
FOR EACH ROW EXECUTE FUNCTION update_product_rating();

-- ───────────────────────────────────────────
--  ORDERS
-- ───────────────────────────────────────────
CREATE TABLE orders (
    id               BIGSERIAL      PRIMARY KEY,
    user_id          BIGINT         NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    total            NUMERIC(14, 2) NOT NULL,
    status           VARCHAR(15)    NOT NULL DEFAULT 'pending',
    payment_method   VARCHAR(50)    NOT NULL,
    shipping_address TEXT           NOT NULL,
    created_at       TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_order_total_nonneg CHECK (total >= 0),
    CONSTRAINT chk_order_status CHECK (
        status IN ('pending','paid','preparing','shipping','delivered','installed')
    )
);

CREATE INDEX idx_orders_user_status ON orders (user_id, status);
CREATE INDEX idx_orders_status      ON orders (status);

-- ───────────────────────────────────────────
--  ORDER ITEMS
-- ───────────────────────────────────────────
-- unit_price se guarda al momento de la compra para preservar historial
-- aunque el precio del producto cambie en el futuro.
-- UNIQUE(order_id, product_id) → no puede haber dos líneas del mismo producto en un pedido.
CREATE TABLE order_items (
    id         BIGSERIAL      PRIMARY KEY,
    order_id   BIGINT         NOT NULL REFERENCES orders(id)   ON DELETE CASCADE,
    product_id BIGINT         NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity   INT            NOT NULL,
    unit_price NUMERIC(12, 2) NOT NULL,
    CONSTRAINT uniq_order_item_product         UNIQUE (order_id, product_id),
    CONSTRAINT chk_order_item_quantity_positive CHECK (quantity > 0),
    CONSTRAINT chk_order_item_price_nonneg      CHECK (unit_price >= 0)
);

CREATE INDEX idx_order_items_order ON order_items (order_id);

-- ───────────────────────────────────────────
--  TRACKING EVENTS
-- ───────────────────────────────────────────
CREATE TABLE tracking_events (
    id          BIGSERIAL    PRIMARY KEY,
    order_id    BIGINT       NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    status      VARCHAR(15)  NOT NULL,
    description TEXT         NOT NULL,
    location    VARCHAR(255) NOT NULL DEFAULT '',
    "timestamp" TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_tracking_status CHECK (
        status IN ('pending','paid','preparing','shipping','delivered','installed')
    )
);

CREATE INDEX idx_tracking_order ON tracking_events (order_id, "timestamp");
