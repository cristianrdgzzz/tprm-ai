# Informe Ejecutivo — Sistema TPRM-AI

**Evaluación automatizada del riesgo de proveedores con protección de datos incorporada**

**Fecha:** 1 de julio de 2026
**Versión:** 1.0
**Estado del proyecto:** Prototipo funcional en entorno de pruebas

---

## 1. Resumen ejecutivo

Toda organización que trabaja con proveedores externos necesita saber si esos
proveedores son seguros y fiables antes de confiarles información o servicios.
Hoy esa comprobación se hace de forma manual: alguien lee los documentos de cada
proveedor, extrae los datos relevantes y rellena una evaluación de riesgo. Es un
trabajo lento, repetitivo y difícil de mantener al día cuando hay muchos
proveedores.

Este proyecto construye un sistema que automatiza esa evaluación. El sistema
recibe los documentos de un proveedor, protege automáticamente los datos
sensibles que contienen, los analiza con inteligencia artificial y genera una
evaluación de riesgo con una puntuación y una recomendación. Toda la información
queda registrada de forma centralizada y trazable.

El resultado esperado es doble: reducir drásticamente el tiempo que hoy consume
evaluar a cada proveedor y aumentar el número de proveedores que la organización
puede revisar, sin renunciar a la protección de los datos ni a la coherencia de
los criterios.

El proyecto se encuentra actualmente en fase de prototipo funcional. El circuito
completo —desde que entra un documento hasta que se genera su evaluación— ya
opera de principio a fin en un entorno de pruebas. Varias mejoras están en
desarrollo, según se detalla al final de este informe.

---

## 2. El problema actual

Antes de trabajar con un proveedor, la organización debe evaluar su nivel de
seguridad: si tiene las certificaciones adecuadas, cómo protege los datos, cómo
responde ante incidentes o si depende de otros subcontratistas. Esta evaluación
se conoce como gestión de riesgo de terceros.

Sin un sistema automatizado, este proceso presenta tres problemas principales.

Es **lento y manual**. Cada proveedor puede aportar varios documentos —
certificados, informes de auditoría, cuestionarios de seguridad— y una persona
debe leerlos, interpretarlos y trasladar la información a una plantilla de
evaluación con decenas de preguntas. Revisar un solo proveedor puede llevar
horas.

Genera **cobertura desigual**. Como cada evaluación requiere tanto esfuerzo, en
la práctica solo se revisan a fondo unos pocos proveedores y muchos quedan sin
evaluar o con evaluaciones desactualizadas.

Implica un **riesgo con los datos sensibles**. Los documentos de los proveedores
contienen nombres de empresas, personas de contacto, correos y otros datos
personales. Manejar y compartir esa información —por ejemplo, al apoyarse en
herramientas de inteligencia artificial— puede exponer datos protegidos si no se
toman precauciones.

A esto se suma la **falta de una visión de conjunto**: sin un inventario
centralizado, resulta difícil saber de un vistazo qué proveedores se han
evaluado, qué puntuación tienen y cuáles requieren atención.

---

## 3. La solución propuesta

El sistema automatiza el ciclo completo de evaluación de un proveedor. Funciona,
en lenguaje de negocio, de la siguiente manera.

**Recibe los documentos del proveedor** en distintos formatos, incluidos
documentos escaneados, de los que es capaz de leer el texto automáticamente.

**Protege los datos sensibles antes de analizarlos.** El sistema detecta y oculta
automáticamente los datos que identifican a personas y empresas —nombres,
correos, ubicaciones, fechas— sustituyéndolos por etiquetas. De este modo, el
análisis posterior trabaja sobre una versión protegida del documento. La
correspondencia entre cada etiqueta y su dato real se guarda de forma segura
dentro de la propia infraestructura de la organización, lo que permite recuperar
la información original cuando es necesario sin exponerla durante el análisis.

**Analiza el documento con inteligencia artificial.** A partir del contenido, el
sistema rellena una evaluación de riesgo estructurada en seis áreas de seguridad
(seguridad de la información, control de accesos, continuidad de negocio,
protección de datos, seguridad en la nube y subcontratistas), asigna una
puntuación y señala las carencias detectadas, incluidas las que impedirían
aprobar al proveedor.

**Restituye los datos reales** una vez completado el análisis, de forma que la
evaluación final muestra la información auténtica del proveedor.

**Centraliza todo en una base de datos** con una ficha por proveedor que incluye
sus datos, su puntuación y su estado (aprobado, aprobado con condiciones,
rechazado o pendiente). El sistema respeta la información ya registrada y solo la
actualiza cuando un documento nuevo aporta datos más completos.

**Genera un inventario general** con todos los proveedores y sus puntuaciones,
que ofrece a los responsables una visión de conjunto y les permite priorizar.

---

## 4. Beneficios clave

| Beneficio | Qué aporta al negocio |
| --- | --- |
| Reducción del tiempo manual | La lectura, extracción de datos y evaluación de cada proveedor se automatiza, liberando al equipo de un trabajo repetitivo. |
| Mayor cobertura de proveedores | Al automatizar el proceso, la organización puede evaluar muchos más proveedores con el mismo esfuerzo. |
| Protección de datos incorporada | Los datos sensibles se ocultan automáticamente antes de cualquier análisis, y la clave para recuperarlos nunca sale de la infraestructura propia, en línea con el RGPD. |
| Trazabilidad y auditoría | De cada documento queda registro de qué se procesó y qué datos se protegieron, lo que facilita demostrar el cumplimiento. |
| Criterios homogéneos | Todas las evaluaciones aplican el mismo marco de referencia (ISO 27001, ENS y RGPD), lo que aporta coherencia y objetividad. |
| Visión centralizada del riesgo | Un único inventario reúne a todos los proveedores y sus puntuaciones, facilitando la priorización y la toma de decisiones. |

Nota: la cuantificación exacta de estos beneficios (por ejemplo, el porcentaje de
tiempo ahorrado por evaluación) **[A definir]**, ya que el sistema aún se
encuentra en entorno de pruebas y no dispone de mediciones sobre volumen real.

---

## 5. Alcance del proyecto

**Dentro del alcance actual** está el circuito completo de evaluación: entrada de
documentos, protección de datos sensibles, análisis de riesgo asistido por
inteligencia artificial, recuperación de los datos reales, almacenamiento
centralizado por proveedor e inventario general con las puntuaciones. Este
circuito ya funciona de principio a fin en el entorno de pruebas.

**Fuera del alcance actual**, y previsto para fases posteriores, se encuentran:
el aprovechamiento del historial de evaluaciones previas para mejorar la calidad
del análisis (actualmente en desarrollo); la generación de un documento de
evaluación individual y detallado por cada proveedor (previsto); la integración
con herramientas corporativas de almacenamiento compartido para que el equipo
acceda desde cualquier lugar (previsto para el futuro; hoy todo opera en local); y
el paso de un entorno de pruebas a un entorno de producción con datos reales.

Es importante señalar que el sistema es hoy un **prototipo de trabajo**, validado
con documentos de ejemplo, y no una solución en producción.

---

## 6. Conclusión

El sistema TPRM-AI aborda una necesidad real y creciente: evaluar el riesgo de los
proveedores de forma rápida, homogénea y respetuosa con la protección de datos.
Su valor estratégico reside en convertir un proceso manual, lento y desigual en
un flujo automatizado, trazable y consistente, que protege la información
sensible por diseño y ofrece una visión centralizada del riesgo de toda la cadena
de proveedores.

En su estado actual, el proyecto ya demuestra que el enfoque funciona de extremo
a extremo. Las siguientes fases se orientan a aumentar la calidad del análisis,
enriquecer los resultados y preparar el sistema para su uso con datos reales.

---

## 7. Estado actual y próximos pasos

**Dónde está el proyecto hoy.** El sistema es un prototipo funcional en entorno de
pruebas, validado con documentos de ejemplo. Ya operan de forma encadenada: la
entrada y lectura de documentos, la protección automática de datos sensibles con
posibilidad de recuperarlos, el análisis de riesgo con inteligencia artificial,
la recuperación de los datos reales, el almacenamiento centralizado por proveedor
y la generación de un inventario general con las puntuaciones.

Conviene precisar, con transparencia, que el análisis de inteligencia artificial
se apoya actualmente en un servicio externo gratuito utilizado para las pruebas.
El principio de protección de datos se mantiene porque a ese servicio solo se le
envía la versión ya protegida del documento, sin datos reales, y la clave para
recuperar la información original permanece siempre en la infraestructura propia.

**En desarrollo actualmente:** el uso del historial de proveedores ya evaluados
para dar más contexto al análisis y mejorar su calidad (el almacenamiento de ese
historial ya está preparado y se está integrando en el circuito principal).

**Previsto en siguientes fases:** mejorar la detección de nombres de personas para
asignar cada documento al proveedor correcto de forma más fiable; afinar el
cálculo automático de la puntuación final; generar un documento de evaluación
individual por proveedor; integrar el sistema con herramientas corporativas de
almacenamiento compartido; y evolucionar del entorno de pruebas a un entorno de
producción preparado para datos reales.

En conjunto, el proyecto ha alcanzado un hito relevante —un circuito completo que
funciona— y tiene por delante un plan de mejoras claras orientadas a la calidad,
la riqueza de los resultados y la puesta en producción.

---

*Sesión 01 completada.*
