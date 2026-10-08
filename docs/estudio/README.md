# Guía de estudio — GridShare

Esta carpeta es una guía en español para entender GridShare a fondo. El código,
los comentarios y la documentación técnica están en inglés (nivel B2) a
propósito, para que el proyecto sea creíble y sirva para practicar. Esta guía
explica el "por qué" de cada decisión en tu idioma, para estudiar con calma.

## Orden sugerido de lectura

1. **[01-mercado-y-subasta.md](01-mercado-y-subasta.md)** — qué es un mercado
   local de energía y cómo funciona la subasta doble de precio uniforme.
2. **[02-pronostico.md](02-pronostico.md)** — por qué hace falta pronosticar y
   cómo lo hace el modelo base.
3. **[03-liquidacion-on-chain.md](03-liquidacion-on-chain.md)** — el contrato
   `GridLedger`, por qué usamos enteros y cómo se protege la privacidad.
4. **[04-arquitectura-y-diseno.md](04-arquitectura-y-diseno.md)** — cómo encajan
   las piezas y qué decisiones de diseño se tomaron.
5. **[05-preguntas-de-entrevista.md](05-preguntas-de-entrevista.md)** — preguntas
   típicas y cómo responderlas con seguridad.

## Resumen en una frase

GridShare simula un vecindario con paneles solares, pronostica cada hora quién
tendrá energía de sobra y quién necesitará energía, los empareja en una subasta
que conviene a las dos partes, y registra cada operación en un contrato
inteligente que todos pueden auditar — sin poner datos personales en la cadena.
