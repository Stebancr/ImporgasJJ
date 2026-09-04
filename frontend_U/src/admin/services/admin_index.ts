export { default as api } from './admin_api'
export { default as authService } from './admin_auth'
export { default as productsService } from './admin_products'
export { default as usersService } from './admin_users'
export { default as brandsService } from './admin_brands'
export { default as categoriesService } from './admin_categories'
export { default as locationsService } from './admin_locations'
export { default as ordersService } from './admin_orders'
export { default as gestionService } from './admin_gestion'
export { visitsService } from './admin_visits'

export type { ProductFilters, CreateProductData } from './admin_products'
export type { UserFilters, CreateUserData, UpdateUserData, SelectOption, CargoNivelRegionalData } from './admin_users'
export type { PublicRegisterData } from './admin_auth'
export type { BrandFilters, CreateBrandData } from './admin_brands'
export type { CategoryFilters, CreateCategoryData } from './admin_categories'
export type { LocationFilters, CreateLocationData } from './admin_locations'
export type { OrderFilters } from './admin_orders'
export type { StockEntry, Cotizacion, Factura, DocumentoItem, CotizacionPayload, FacturaPayload } from './admin_gestion'
export type {
  ClienteVisita, Tecnico, VisitaItem, VisitaDetalle, CreateVisitaData, UpdateVisitaData,
  CalendarioData, CalendarioItem, ReporteVisita, EvidenciaFoto,
} from './admin_visits'
