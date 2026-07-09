# Proyecto Flame_System

Sistema para inventario y control de ventas de comidas rapidas con alertas    

## Tecnologias usadas
- `Python` v3.14
- `Django` v6.0.3

## Instalación

• Clonar este repositorio

```bash
git clone https://github.com/Cristian-Gomez-cristforx/Project_Flame_System_django.git
```

• Instalar las dependencias:

```bash
pip install -r requirements.txt**
```

## Configuración inicial

1. **Archivo .env:**
   - Crear el archivo,django no lo crea por defecto
   - Pedir las configuraciones que guarda este archivo(no se sube)
2. **Carpeta de entorno virtual(venv):** 
   - Cree su propio entorno virutal, para mejor manejo de librerías y dependecias y evitar conflictos con ciertas versiones.
   - Asegurese siempre de ejecutar el proyecto dentro de su entorno, debe salir la ruta dentro de "venv".
   - Use requeriments.txt para configurarlo rapidamente.

## Desarrollo

1. **Registrar siempre en settings las apps que se creen:** 
   - Una app se crea usando el comando -> python manage.py startapp "nombre que le quiera asignar".
   - Dentro del proyecto, en "INSTALLED APPS", coloque el nombre que le colocó a su app. 
2. **Crear templates y static, para luego configurarlos:**
   - Django tiene en settings para pasarle donde se ubican, y poder leerlos,tenga en cuenta que tiene que crear eso usted mismo y luego definirlo,como se hace con las apps.