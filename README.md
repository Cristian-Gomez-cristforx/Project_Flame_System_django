###Proyecto Flame_System
>Sistema para inventario y control de ventas de comidas rapidas<br> con alertas    
***

###Tecnologias usadas
>***Version del lenguaje***
>- ***Python***= 3.14 version
>- **FrameworK**=Django 6.0.3 version
**NOTA:** Puede consultar las dependecias y librerias, por medio del archivo de requerimietos.

El archivo de requeriments lo tendra al clonar este repo, ayudara a instalar las dependencias adicionales para ahorrar tiempo, de manera automatica.
***

>  para ello usar el siguiente comando:
> - **pip install -r requirements.txt**
***


##Aclaraciones:
>Algunas cosas requieren instalacion manual, las cuales encontrara aqui descritas,las dependencias y otras librerias,se instalan automaticamente, ejecutando el archivo de requeriments. El cual puede ver tambien lo que contiene a continuacion.

>[Ver requirements.txt](./requirements.txt)
***

- **Configuraciones ajenas del repositorio (otros archivos)** 
1. **Archivo .env:**
   - Crear el archivo,django no lo crea por defecto
   - Pedir las configuraciones que guarda este archivo(no se sube)
2. **Carpeta de entorno virtual(venv):** 
   - Cree su propio entorno virutal,para mejor manejo de librerias y dependecias y evitar conflictos con ciertas versiones.Por lo general más util si maneja mas proyectos en su localhost.
   - Asegurese siempre de ejecutar el proyecto dentro de su entorno,debe salir la ruta dentro de "venv".
   - Use requeriments.txt para configurarlo rapidamente.
3. **Registrar siempre en settings las apps que se creen:** 
   - Una app se crea usando el comando -> python manage.py startapp "nombre que le quiera asignar".
   - Dentro del proyecto, en "INSTALLED APPS", coloque el nombre que le colocó a su app. 
4. **Crear templates y static, para luego configurarlos:**
   - Django tiene en settings para pasarle donde se ubican, y poder leerlos,tenga en cuenta que tiene que crear eso usted mismo y luego definirlo,como se hace con las apps.