"""
Protocolo de pruebas - API Usuarios
=====================================
Cubre todos los endpoints definidos en usuarios/urls.py:

  POST/GET/PUT  /user/register/<id>/
  POST          /user/registerTemporal/
  POST          /user/registrar-masivo/
  GET/PATCH     /user/perfil/  y  /user/perfil/<id>/
  GET           /user/lista-usuarios/
  GET           /user/cargo-Nivel-Regional/
  GET           /user/filtrar-usuarios/
  POST/PATCH    /user/cambiar-estado-usuario/  y  /user/cambiar-estado-usuario/<id>/
  PATCH         /user/actualizar-rol-usuario/<id>/
  GET/POST/PUT/DELETE  /user/Cargo/
  GET/POST/PUT/DELETE  /user/Nivel/
  GET/POST/PUT/DELETE  /user/Region/
  GET           /user/reporte-usuarios/

Tipos de usuario:
  0: Colaborador normal
  1: Administrador
  2: Lectura Admin
  3: Usuario Especial
  4: Super Admin

Estrategia: force_authenticate() para aislar la lógica de negocio del flujo JWT.
"""

import io
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from usuarios.models import Usuarios, Colaboradores, Cargo, Niveles, Regional


# ──────────────────────────────────────────────
#  Helpers de creación de fixtures
# ──────────────────────────────────────────────

def _crear_cargo(nombre="Paramédico"):
    return Cargo.objects.create(nombrecargo=nombre, estadocargo=1)


def _crear_nivel(nombre="Básico"):
    return Niveles.objects.create(nombrenivel=nombre, estadonivel=1)


def _crear_regional(nombre="Bogotá"):
    return Regional.objects.create(nombreregional=nombre, estadoregional=1)


def _crear_colaborador(cc="11111111", nombre="Test", apellido="Colab",
                        cargo=None, nivel=None, regional=None):
    return Colaboradores.objects.create(
        cccolaborador=cc,
        nombrecolaborador=nombre,
        apellidocolaborador=apellido,
        correocolaborador=f"{cc}@test.com",
        telefocolaborador="3000000000",
        cargocolaborador=cargo,
        nivelcolaborador=nivel,
        regionalcolab=regional,
        estadocolaborador=1,
    )


def _crear_usuario(usuario="admin_test", tipousuario=4, colaborador=None):
    u = Usuarios(
        usuario=usuario,
        tipousuario=tipousuario,
        estadousuario=1,
        idcolaboradoru=colaborador,
    )
    u.set_password("TestPass@1234")
    u.save()
    return u


# ──────────────────────────────────────────────
#  PERFIL
# ──────────────────────────────────────────────

class PerfilTests(APITestCase):
    """Pruebas de GET/PATCH /user/perfil/ y /user/perfil/<id>/"""

    def setUp(self):
        self.client = APIClient()
        self.cargo = _crear_cargo()
        self.nivel = _crear_nivel()
        self.regional = _crear_regional()
        self.colab = _crear_colaborador(
            cargo=self.cargo, nivel=self.nivel, regional=self.regional
        )
        self.user = _crear_usuario(colaborador=self.colab)
        self.client.force_authenticate(user=self.user)

    # ── Autenticación ──────────────────────────

    def test_get_sin_autenticacion_retorna_401(self):
        cliente = APIClient()
        resp = cliente.get(reverse("perfil"))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    # ── GET propio ─────────────────────────────

    def test_get_perfil_propio_retorna_200(self):
        resp = self.client.get(reverse("perfil"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["id_colaborador"], self.colab.idcolaborador)

    def test_get_perfil_propio_incluye_campos(self):
        resp = self.client.get(reverse("perfil"))
        for campo in ["nombre_colaborador", "apellido_colaborador",
                      "nombre_cargo", "nombre_nivel", "nombre_regional"]:
            self.assertIn(campo, resp.data)

    def test_get_perfil_usuario_sin_colaborador_retorna_400(self):
        """Usuario sin colaborador asociado debe recibir 400."""
        user_sin_colab = _crear_usuario("sin_colab", tipousuario=2)
        self.client.force_authenticate(user=user_sin_colab)
        resp = self.client.get(reverse("perfil"))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ── GET por ID ─────────────────────────────

    def test_get_perfil_por_id_existente(self):
        resp = self.client.get(
            reverse("perfil-especifico", kwargs={"id": self.colab.idcolaborador})
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["id_colaborador"], self.colab.idcolaborador)

    def test_get_perfil_por_id_inexistente_retorna_400(self):
        resp = self.client.get(
            reverse("perfil-especifico", kwargs={"id": 99999})
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ── PATCH ──────────────────────────────────

    def test_patch_alterna_estado_colaborador(self):
        """PATCH alterna estado del colaborador: 1 → 0."""
        resp = self.client.patch(
            reverse("perfil-especifico", kwargs={"id": self.colab.idcolaborador})
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.colab.refresh_from_db()
        self.assertEqual(self.colab.estadocolaborador, 0)

    def test_patch_sin_id_retorna_400(self):
        resp = self.client.patch(reverse("perfil"))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_id_inexistente_retorna_404(self):
        resp = self.client.patch(
            reverse("perfil-especifico", kwargs={"id": 99999})
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


# ──────────────────────────────────────────────
#  REGISTER (POST / GET / PUT)
# ──────────────────────────────────────────────

class RegisterTests(APITestCase):
    """Pruebas de POST /user/register/ y GET/PUT /user/register/<id>/"""

    def setUp(self):
        self.client = APIClient()
        self.cargo = _crear_cargo()
        self.nivel = _crear_nivel()
        self.regional = _crear_regional()
        # El endpoint requiere IsSuperAdmin + IsAdminUser → tipousuario 4
        self.admin = _crear_usuario("superadm", tipousuario=4)
        self.client.force_authenticate(user=self.admin)
        self.url_post = reverse("register")

    def _payload_valido(self, usuario="nuevo_usr", cc="22222222"):
        return {
            "usuario": usuario,
            "password": "Clave@5678",
            "is_staff": 0,
            "idcolaborador": {
                "cc_colaborador": cc,
                "nombre_colaborador": "Nuevo",
                "apellido_colaborador": "Usuario",
                "cargo_colaborador": self.cargo.idcargo,
                "correo_colaborador": f"{cc}@test.com",
                "telefo_colaborador": "3101234567",
                "nivel_colaborador": self.nivel.idnivel,
                "regional_colab": self.regional.idregional,
            }
        }

    # ── Autenticación ──────────────────────────

    def test_post_sin_autenticacion_retorna_401(self):
        resp = APIClient().post(self.url_post, {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    # ── POST ───────────────────────────────────

    def test_post_crea_usuario_y_colaborador(self):
        resp = self.client.post(self.url_post, self._payload_valido(), format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn("usuario_id", resp.json())
        self.assertIn("colaborador_id", resp.json())

    def test_post_usuario_duplicado_retorna_400(self):
        self.client.post(self.url_post, self._payload_valido(), format="json")
        resp = self.client.post(
            self.url_post,
            self._payload_valido(usuario="nuevo_usr", cc="33333333"),
            format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_cedula_duplicada_retorna_400(self):
        self.client.post(self.url_post, self._payload_valido(), format="json")
        resp = self.client.post(
            self.url_post,
            self._payload_valido(usuario="otro_usr", cc="22222222"),
            format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_sin_campos_requeridos_retorna_400(self):
        resp = self.client.post(self.url_post, {"usuario": "x"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_sin_datos_colaborador_retorna_400(self):
        payload = {"usuario": "x2", "password": "p", "idcolaborador": {}}
        resp = self.client.post(self.url_post, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ── GET por colaborador_id ──────────────────

    def test_get_colaborador_existente(self):
        colab = _crear_colaborador(
            "55555555", cargo=self.cargo, nivel=self.nivel, regional=self.regional
        )
        resp = self.client.get(
            reverse("register", kwargs={"colaborador_id": colab.idcolaborador})
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["nombre"], "Test")

    def test_get_colaborador_inexistente_retorna_404(self):
        resp = self.client.get(
            reverse("register", kwargs={"colaborador_id": 99999})
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # ── PUT por colaborador_id ──────────────────

    def test_put_actualiza_colaborador(self):
        colab = _crear_colaborador(
            "66666666", cargo=self.cargo, nivel=self.nivel, regional=self.regional
        )
        resp = self.client.put(
            reverse("register", kwargs={"colaborador_id": colab.idcolaborador}),
            {"correo": "nuevo@correo.com"},
            format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        colab.refresh_from_db()
        self.assertEqual(colab.correocolaborador, "nuevo@correo.com")

    def test_put_colaborador_inexistente_retorna_404(self):
        resp = self.client.put(
            reverse("register", kwargs={"colaborador_id": 99999}),
            {"correo": "x@x.com"},
            format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


# ──────────────────────────────────────────────
#  REGISTER TEMPORAL
# ──────────────────────────────────────────────

class RegisterTemporalTests(APITestCase):
    """Pruebas de POST /user/registerTemporal/"""

    def setUp(self):
        self.client = APIClient()
        # IsSuperAdmin + IsUsuarioEspecial → tipo 4 cumple ambas
        self.admin = _crear_usuario("superadm_tmp", tipousuario=4)
        self.client.force_authenticate(user=self.admin)
        self.url = reverse("register_temporal")

    def _payload(self, usuario="tmp_usr", cc="77777777"):
        return {
            "usuario": usuario,
            "password": "Temporal@1",
            "idcolaborador": {
                "cc_colaborador": cc,
                "nombre_colaborador": "Temp",
                "apellido_colaborador": "User",
            }
        }

    def test_post_crea_usuario_temporal(self):
        resp = self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.json()["mensaje"], "Usuario temporal creado")

    def test_post_usuario_duplicado_retorna_400(self):
        self.client.post(self.url, self._payload(), format="json")
        resp = self.client.post(
            self.url, self._payload(usuario="tmp_usr", cc="88888888"), format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_sin_campos_minimos_retorna_400(self):
        resp = self.client.post(
            self.url,
            {"usuario": "x3", "password": "p", "idcolaborador": {}},
            format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_sin_autenticacion_retorna_401(self):
        resp = APIClient().post(self.url, {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


# ──────────────────────────────────────────────
#  LISTA USUARIOS
# ──────────────────────────────────────────────

class ListaUsuariosTests(APITestCase):
    """Pruebas de GET /user/lista-usuarios/"""

    def setUp(self):
        self.client = APIClient()
        self.admin = _crear_usuario("admin_lista", tipousuario=4)
        self.client.force_authenticate(user=self.admin)
        self.url = reverse("lista_usuarios")

    def test_get_sin_autenticacion_retorna_401(self):
        resp = APIClient().get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_retorna_estructura_paginada(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for key in ["count", "page", "page_size", "results"]:
            self.assertIn(key, resp.data)

    def test_get_lista_vacia(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.data["count"], 0)

    def test_get_lista_con_colaboradores_activos(self):
        cargo = _crear_cargo("Enfermero")
        _crear_colaborador("10001001", cargo=cargo)
        _crear_colaborador("10001002", cargo=cargo)
        resp = self.client.get(self.url)
        self.assertGreaterEqual(resp.data["count"], 2)

    def test_get_busqueda_por_nombre(self):
        cargo = _crear_cargo("Piloto")
        colab = _crear_colaborador("10002001", nombre="Zara", apellido="Ruiz", cargo=cargo)
        resp = self.client.get(self.url, {"search": "Zara"})
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["nombre_colaborador"], "Zara")

    def test_get_paginacion_page_size(self):
        cargo = _crear_cargo("Tecnico")
        for i in range(12):
            _crear_colaborador(str(20000000 + i), cargo=cargo)
        resp = self.client.get(self.url, {"page": 1, "page_size": 5})
        self.assertEqual(len(resp.data["results"]), 5)
        self.assertEqual(resp.data["page_size"], 5)


# ──────────────────────────────────────────────
#  CARGO / NIVEL / REGIONAL
# ──────────────────────────────────────────────

class DatosCargoTests(APITestCase):
    """Pruebas de GET/POST/PUT/DELETE /user/Cargo/"""

    def setUp(self):
        self.client = APIClient()
        self.admin = _crear_usuario("admin_cargo", tipousuario=4)
        self.client.force_authenticate(user=self.admin)
        self.url = reverse("datos-cargo")

    # ── GET ────────────────────────────────────

    def test_get_retorna_lista_cargos_activos(self):
        _crear_cargo("Médico")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("count", resp.data)
        self.assertIn("results", resp.data)

    def test_get_no_devuelve_cargos_inactivos(self):
        Cargo.objects.create(nombrecargo="Inactivo", estadocargo=0)
        resp = self.client.get(self.url)
        nombres = [c["nombrecargo"] for c in resp.data["results"]]
        self.assertNotIn("Inactivo", nombres)

    # ── POST ───────────────────────────────────

    def test_post_crea_cargo(self):
        resp = self.client.post(self.url, {"nombrecargo": "Conductor"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Cargo.objects.filter(nombrecargo="Conductor").exists())

    def test_post_cargo_duplicado_retorna_400(self):
        _crear_cargo("Duplicado")
        resp = self.client.post(self.url, {"nombrecargo": "Duplicado"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_sin_nombre_retorna_400(self):
        resp = self.client.post(self.url, {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ── PUT ────────────────────────────────────

    def test_put_actualiza_cargo(self):
        cargo = _crear_cargo("OldCargo")
        resp = self.client.put(
            self.url,
            {"idcargo": cargo.idcargo, "nombrecargo": "NewCargo"},
            format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        cargo.refresh_from_db()
        self.assertEqual(cargo.nombrecargo, "NewCargo")

    def test_put_cargo_inexistente_retorna_404(self):
        resp = self.client.put(
            self.url,
            {"idcargo": 99999, "nombrecargo": "X"},
            format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_put_sin_idcargo_retorna_400(self):
        resp = self.client.put(self.url, {"nombrecargo": "Sin id"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ── DELETE ─────────────────────────────────

    def test_delete_desactiva_cargo(self):
        cargo = _crear_cargo("A Desactivar")
        resp = self.client.delete(self.url, {"idcargo": cargo.idcargo}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        cargo.refresh_from_db()
        self.assertEqual(cargo.estadocargo, 0)

    def test_delete_cargo_inexistente_retorna_404(self):
        resp = self.client.delete(self.url, {"idcargo": 99999}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_sin_autenticacion_retorna_401(self):
        resp = APIClient().get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class DatosNivelTests(APITestCase):
    """Pruebas de GET/POST/PUT/DELETE /user/Nivel/"""

    def setUp(self):
        self.client = APIClient()
        self.admin = _crear_usuario("admin_nivel", tipousuario=4)
        self.client.force_authenticate(user=self.admin)
        self.url = reverse("datos-nivel")

    def test_get_retorna_lista_niveles(self):
        _crear_nivel("Avanzado")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(resp.data["count"], 1)

    def test_post_crea_nivel(self):
        resp = self.client.post(self.url, {"nombrenivel": "Intermedio"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_post_nivel_duplicado_retorna_400(self):
        _crear_nivel("Dup")
        resp = self.client.post(self.url, {"nombrenivel": "Dup"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_sin_nombre_retorna_400(self):
        resp = self.client.post(self.url, {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_actualiza_nivel(self):
        nivel = _crear_nivel("OldNivel")
        resp = self.client.put(
            self.url,
            {"idnivel": nivel.idnivel, "nombrenivel": "NewNivel"},
            format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        nivel.refresh_from_db()
        self.assertEqual(nivel.nombrenivel, "NewNivel")

    def test_put_nivel_inexistente_retorna_404(self):
        resp = self.client.put(
            self.url, {"idnivel": 99999, "nombrenivel": "X"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_desactiva_nivel(self):
        nivel = _crear_nivel("NivelDel")
        resp = self.client.delete(self.url, {"idnivel": nivel.idnivel}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        nivel.refresh_from_db()
        self.assertEqual(nivel.estadonivel, 0)

    def test_delete_nivel_inexistente_retorna_404(self):
        resp = self.client.delete(self.url, {"idnivel": 99999}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class DatosRegionTests(APITestCase):
    """Pruebas de GET/POST/PUT/DELETE /user/Region/"""

    def setUp(self):
        self.client = APIClient()
        self.admin = _crear_usuario("admin_region", tipousuario=4)
        self.client.force_authenticate(user=self.admin)
        self.url = reverse("datos-region")

    def test_get_retorna_lista_regionales(self):
        _crear_regional("Medellin")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(resp.data["count"], 1)

    def test_post_crea_regional(self):
        resp = self.client.post(self.url, {"nombreregional": "Cali"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_post_regional_duplicada_retorna_400(self):
        _crear_regional("DupReg")
        resp = self.client.post(self.url, {"nombreregional": "DupReg"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_sin_nombre_retorna_400(self):
        resp = self.client.post(self.url, {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_actualiza_regional(self):
        regional = _crear_regional("OldRegion")
        resp = self.client.put(
            self.url,
            {"idregional": regional.idregional, "nombreregional": "NewRegion"},
            format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        regional.refresh_from_db()
        self.assertEqual(regional.nombreregional, "NewRegion")

    def test_put_regional_inexistente_retorna_404(self):
        resp = self.client.put(
            self.url, {"idregional": 99999, "nombreregional": "X"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_desactiva_regional(self):
        regional = _crear_regional("RegDel")
        resp = self.client.delete(
            self.url, {"idregional": regional.idregional}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        regional.refresh_from_db()
        self.assertEqual(regional.estadoregional, 0)

    def test_delete_regional_inexistente_retorna_404(self):
        resp = self.client.delete(self.url, {"idregional": 99999}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


# ──────────────────────────────────────────────
#  CARGO / NIVEL / REGIONAL (datos compartidos)
# ──────────────────────────────────────────────

class CargoNivelRegionalViewTests(APITestCase):
    """Pruebas de GET /user/cargo-Nivel-Regional/"""

    def setUp(self):
        self.client = APIClient()
        self.admin = _crear_usuario("admin_cnr", tipousuario=4)
        self.client.force_authenticate(user=self.admin)
        self.url = reverse("cargo-nivel-regional")

    def test_get_sin_autenticacion_retorna_401(self):
        resp = APIClient().get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_retorna_cargos_niveles_regionales(self):
        _crear_cargo("Aux")
        _crear_nivel("Inicial")
        _crear_regional("Sur")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for key in ["cargos", "niveles", "regionales"]:
            self.assertIn(key, resp.data)

    def test_get_solo_devuelve_activos(self):
        Cargo.objects.create(nombrecargo="Inact", estadocargo=0)
        resp = self.client.get(self.url)
        nombres = [c["nombrecargo"] for c in resp.data["cargos"]]
        self.assertNotIn("Inact", nombres)


# ──────────────────────────────────────────────
#  FILTRAR USUARIOS
# ──────────────────────────────────────────────

class FiltrarUsuariosTests(APITestCase):
    """Pruebas de GET /user/filtrar-usuarios/"""

    def setUp(self):
        self.client = APIClient()
        self.admin = _crear_usuario("admin_filtrar", tipousuario=4)
        self.client.force_authenticate(user=self.admin)
        self.url = reverse("filtrar-usuarios")
        cargo = _crear_cargo("Bombero")
        self.colab = _crear_colaborador("30001001", nombre="Felipe", apellido="Mora", cargo=cargo)

    def test_get_sin_autenticacion_retorna_401(self):
        resp = APIClient().get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_retorna_todos_sin_filtro(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(resp.data["count"], 1)

    def test_get_filtra_por_nombre(self):
        resp = self.client.get(self.url, {"q": "Felipe"})
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["nombre_colaborador"], "Felipe")

    def test_get_filtra_por_cedula(self):
        resp = self.client.get(self.url, {"q": "30001001"})
        self.assertEqual(resp.data["count"], 1)

    def test_get_sin_resultados(self):
        resp = self.client.get(self.url, {"q": "XXXXXX"})
        self.assertEqual(resp.data["count"], 0)

    def test_get_paginacion(self):
        cargo = _crear_cargo("Rescatista")
        for i in range(8):
            _crear_colaborador(str(40000000 + i), cargo=cargo)
        resp = self.client.get(self.url, {"page": 1, "page_size": 3})
        self.assertLessEqual(len(resp.data["results"]), 3)


# ──────────────────────────────────────────────
#  CAMBIAR ESTADO USUARIO
# ──────────────────────────────────────────────

class CambiarEstadoUsuarioTests(APITestCase):
    """Pruebas de PATCH /user/cambiar-estado-usuario/<id>/ y POST /user/cambiar-estado-usuario/"""

    def setUp(self):
        self.client = APIClient()
        # IsSuperAdmin → tipo 1,2,3,4; para superadmin puro usamos 4
        self.admin = _crear_usuario("admin_estado", tipousuario=4)
        self.client.force_authenticate(user=self.admin)

        cargo = _crear_cargo("Logística")
        self.colab = _crear_colaborador("50001001", cargo=cargo)
        self.usuario_colab = _crear_usuario("user_colab1", tipousuario=0, colaborador=self.colab)

    def test_patch_sin_autenticacion_retorna_401(self):
        url = reverse("cambiar-estado-usuario", kwargs={"colaborador_id": self.colab.idcolaborador})
        resp = APIClient().patch(url, {"estado": 0}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patch_desactiva_usuario(self):
        url = reverse("cambiar-estado-usuario", kwargs={"colaborador_id": self.colab.idcolaborador})
        resp = self.client.patch(url, {"estado": 0}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.usuario_colab.refresh_from_db()
        self.assertEqual(self.usuario_colab.estadousuario, 0)

    def test_patch_activa_usuario(self):
        self.usuario_colab.estadousuario = 0
        self.usuario_colab.save()
        url = reverse("cambiar-estado-usuario", kwargs={"colaborador_id": self.colab.idcolaborador})
        resp = self.client.patch(url, {"estado": 1}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.usuario_colab.refresh_from_db()
        self.assertEqual(self.usuario_colab.estadousuario, 1)

    def test_patch_estado_invalido_retorna_400(self):
        url = reverse("cambiar-estado-usuario", kwargs={"colaborador_id": self.colab.idcolaborador})
        resp = self.client.patch(url, {"estado": 99}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_sin_campo_estado_retorna_400(self):
        url = reverse("cambiar-estado-usuario", kwargs={"colaborador_id": self.colab.idcolaborador})
        resp = self.client.patch(url, {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_colaborador_inexistente_retorna_404(self):
        url = reverse("cambiar-estado-usuario", kwargs={"colaborador_id": 99999})
        resp = self.client.patch(url, {"estado": 0}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # ── POST masivo ────────────────────────────

    def test_post_masivo_por_colaborador_ids(self):
        url = reverse("cambiar-estado-usuario-post")
        resp = self.client.post(
            url,
            {"colaborador_ids": [self.colab.idcolaborador], "estado": 0},
            format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("actualizados", resp.data)
        self.assertEqual(resp.data["actualizados"], 1)

    def test_post_masivo_por_cedulas(self):
        url = reverse("cambiar-estado-usuario-post")
        resp = self.client.post(
            url,
            {"cedulas": [self.colab.cccolaborador], "estado": 1},
            format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["actualizados"], 1)

    def test_post_masivo_sin_ids_retorna_400(self):
        url = reverse("cambiar-estado-usuario-post")
        resp = self.client.post(url, {"estado": 0}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_masivo_sin_estado_retorna_400(self):
        url = reverse("cambiar-estado-usuario-post")
        resp = self.client.post(
            url,
            {"colaborador_ids": [self.colab.idcolaborador]},
            format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_masivo_id_inexistente_registrado_en_no_encontrados(self):
        url = reverse("cambiar-estado-usuario-post")
        resp = self.client.post(
            url,
            {"colaborador_ids": [99999], "estado": 0},
            format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreater(resp.data["no_encontrados"], 0)


# ──────────────────────────────────────────────
#  ACTUALIZAR ROL USUARIO
# ──────────────────────────────────────────────

class ActualizarRolUsuarioTests(APITestCase):
    """Pruebas de PATCH /user/actualizar-rol-usuario/<id>/"""

    def setUp(self):
        self.client = APIClient()
        self.superadmin = _crear_usuario("superadm_rol", tipousuario=4)
        self.client.force_authenticate(user=self.superadmin)
        cargo = _crear_cargo("Operaciones")
        self.colab = _crear_colaborador("60001001", cargo=cargo)
        self.usuario = _crear_usuario("user_rol_test", tipousuario=0, colaborador=self.colab)

    def test_patch_sin_autenticacion_retorna_401(self):
        url = reverse("actualizar-rol-usuario", kwargs={"colaborador_id": self.colab.idcolaborador})
        resp = APIClient().patch(url, {"tipousuario": 1}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patch_actualiza_rol(self):
        url = reverse("actualizar-rol-usuario", kwargs={"colaborador_id": self.colab.idcolaborador})
        resp = self.client.patch(url, {"tipousuario": 1}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.tipousuario, 1)

    def test_patch_rol_invalido_retorna_400(self):
        url = reverse("actualizar-rol-usuario", kwargs={"colaborador_id": self.colab.idcolaborador})
        resp = self.client.patch(url, {"tipousuario": 99}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_sin_campo_tipousuario_retorna_400(self):
        url = reverse("actualizar-rol-usuario", kwargs={"colaborador_id": self.colab.idcolaborador})
        resp = self.client.patch(url, {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_colaborador_inexistente_retorna_404(self):
        url = reverse("actualizar-rol-usuario", kwargs={"colaborador_id": 99999})
        resp = self.client.patch(url, {"tipousuario": 1}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_respuesta_incluye_rol_anterior_y_nuevo(self):
        url = reverse("actualizar-rol-usuario", kwargs={"colaborador_id": self.colab.idcolaborador})
        resp = self.client.patch(url, {"tipousuario": 2}, format="json")
        self.assertIn("rol_anterior", resp.data)
        self.assertIn("nuevo_rol", resp.data)
        self.assertEqual(resp.data["rol_anterior"], 0)
        self.assertEqual(resp.data["nuevo_rol"], 2)


# ──────────────────────────────────────────────
#  REGISTRAR MASIVO (CSV)
# ──────────────────────────────────────────────

class RegistrarMasivoTests(APITestCase):
    """Pruebas de POST /user/registrar-masivo/"""

    def setUp(self):
        self.client = APIClient()
        self.admin = _crear_usuario("admin_masivo", tipousuario=4)
        self.client.force_authenticate(user=self.admin)
        self.url = reverse("registrar-masivo")
        self.cargo = _crear_cargo("Socorrista")
        self.nivel = _crear_nivel("Junior")
        self.regional = _crear_regional("Norte")

    def _csv_file(self, contenido, nombre="test.csv"):
        f = io.BytesIO(contenido.encode("utf-8"))
        f.name = nombre
        return f

    def _csv_valido(self, cedula="70001001"):
        return (
            "cedula;Nombre;Correo;Numero;Region;Nivel;Cargo\n"
            f"{cedula};Apellido1 Apellido2 Nombre1;{cedula}@test.com;"
            f"3001111111;{self.regional.nombreregional};"
            f"{self.nivel.nombrenivel};{self.cargo.nombrecargo}\n"
        )

    def test_post_sin_autenticacion_retorna_401(self):
        resp = APIClient().post(self.url, {})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_post_sin_archivo_retorna_400(self):
        resp = self.client.post(self.url, {}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_archivo_no_csv_retorna_400(self):
        f = io.BytesIO(b"data")
        f.name = "archivo.xlsx"
        resp = self.client.post(self.url, {"archivo": f}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_csv_valido_crea_usuarios(self):
        f = self._csv_file(self._csv_valido("80001001"))
        resp = self.client.post(self.url, {"archivo": f}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Colaboradores.objects.filter(cccolaborador="80001001").exists())

    def test_post_csv_cedula_duplicada_reporta_error(self):
        _crear_colaborador("80002001")
        f = self._csv_file(self._csv_valido("80002001"))
        resp = self.client.post(self.url, {"archivo": f}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        # El registro duplicado debe aparecer en detalles_errores
        data = resp.json()
        self.assertIn("detalles_errores", data)


# ──────────────────────────────────────────────
#  REPORTE USUARIOS (Excel)
# ──────────────────────────────────────────────

class ReporteUsuariosTests(APITestCase):
    """Pruebas de GET /user/reporte-usuarios/"""

    def setUp(self):
        self.client = APIClient()
        self.admin = _crear_usuario("admin_reporte", tipousuario=4)
        self.client.force_authenticate(user=self.admin)
        self.url = reverse("reporte-usuarios")

    def test_get_sin_autenticacion_retorna_401(self):
        resp = APIClient().get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_retorna_archivo_excel(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        content_type = resp.get("Content-Type", "")
        self.assertIn("spreadsheetml", content_type)

    def test_get_retorna_header_content_disposition(self):
        resp = self.client.get(self.url)
        self.assertIn("Content-Disposition", resp)
        self.assertIn(".xlsx", resp["Content-Disposition"])
