-- pgvector queda listo para la fase RAG con n8n
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE personas (
    nro_documento    VARCHAR(10) PRIMARY KEY,           -- llave de búsqueda
    tipo_documento   VARCHAR(30) NOT NULL CHECK (tipo_documento IN ('Tarjeta de identidad','Cédula','T.I','C.C')),
    primer_nombre    VARCHAR(30) NOT NULL,
    segundo_nombre   VARCHAR(30),
    apellidos        VARCHAR(60) NOT NULL,
    fecha_nacimiento DATE        NOT NULL,
    genero           VARCHAR(30) NOT NULL
        CHECK (genero IN ('Masculino','Femenino','femenino','No binario','Prefiero no reportar')),
    correo           VARCHAR(254) NOT NULL,
    celular          CHAR(10)    NOT NULL,
    foto             BYTEA,
    foto_tipo        VARCHAR(50),
    creado_en        TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE logs (
    id                BIGSERIAL PRIMARY KEY,
    tipo_transaccion  VARCHAR(20) NOT NULL CHECK (tipo_transaccion IN ('CREAR','MODIFICAR','CONSULTAR','BORRAR','RAG','CONSULTA_NL')),
    documento         VARCHAR(20) NOT NULL,   -- '*' cuando es un listado o consulta general
    usuario           VARCHAR(100) NOT NULL,
    detalle           TEXT,
    fecha             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_logs_doc   ON logs (documento);
CREATE INDEX idx_logs_tipo  ON logs (tipo_transaccion);
CREATE INDEX idx_logs_fecha ON logs (fecha);

-- Usuario para n8n con acceso de lectura a personas y permisos para registrar logs de RAG
CREATE ROLE n8n_ro LOGIN PASSWORD 'n8n_ro_pass';
GRANT CONNECT ON DATABASE personas_db TO n8n_ro;
GRANT USAGE ON SCHEMA public TO n8n_ro;
GRANT SELECT (nro_documento, tipo_documento, primer_nombre, segundo_nombre, apellidos,
              fecha_nacimiento, genero, correo, celular, creado_en) ON personas TO n8n_ro;
GRANT SELECT, INSERT ON TABLE logs TO n8n_ro;
GRANT USAGE, SELECT ON SEQUENCE logs_id_seq TO n8n_ro;
GRANT CREATE ON SCHEMA public TO n8n_ro;

-- Datos iniciales de prueba (incluye el caso del enunciado: Pedro Pérez)
INSERT INTO personas (tipo_documento, nro_documento, primer_nombre, segundo_nombre, apellidos, fecha_nacimiento, genero, correo, celular)
VALUES 
    ('Cédula', '1001', 'Pedro', NULL, 'Pérez', '2001-03-05', 'Masculino', 'pedro.perez@example.com', '3001234567'),
    ('Cédula', '1002', 'Ana', 'María', 'Gómez', '1995-07-20', 'Femenino', 'ana.gomez@example.com', '3109876543'),
    ('Tarjeta de identidad', '1003', 'Carlos', 'Eduardo', 'Rodríguez', '1998-11-15', 'Masculino', 'carlos.rodriguez@example.com', '3205551234')
ON CONFLICT (nro_documento) DO NOTHING;

INSERT INTO logs (tipo_transaccion, documento, usuario, detalle)
VALUES
    ('CREAR', '1001', 'sistema', 'Carga inicial: Pedro Pérez'),
    ('CREAR', '1002', 'sistema', 'Carga inicial: Ana María Gómez'),
    ('CREAR', '1003', 'sistema', 'Carga inicial: Carlos Eduardo Rodríguez')
ON CONFLICT DO NOTHING;
