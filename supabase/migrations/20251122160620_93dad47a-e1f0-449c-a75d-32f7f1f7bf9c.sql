-- Crear enum para roles
CREATE TYPE public.app_role AS ENUM ('colaborador', 'analista_rrhh');

-- Crear enum para estados de descanso médico
CREATE TYPE public.estado_descanso AS ENUM ('Pendiente', 'Aprobado', 'Rechazado');

-- Crear enum para categorías de colaboradores
CREATE TYPE public.categoria_colaborador AS ENUM ('A', 'B', 'C', 'D');

-- Crear enum para sexo
CREATE TYPE public.sexo_colaborador AS ENUM ('M', 'F');

-- Tabla de roles de usuario
CREATE TABLE public.user_roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  role app_role NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
  UNIQUE(user_id, role)
);

ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;

-- Función de seguridad para verificar roles
CREATE OR REPLACE FUNCTION public.has_role(_user_id UUID, _role app_role)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.user_roles
    WHERE user_id = _user_id AND role = _role
  )
$$;

-- Tabla de perfiles de usuario
CREATE TABLE public.profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  dni VARCHAR(8) NOT NULL UNIQUE,
  apellidos TEXT NOT NULL,
  nombres TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- Políticas RLS para profiles
CREATE POLICY "Users can view their own profile"
  ON public.profiles FOR SELECT
  USING (auth.uid() = id);

CREATE POLICY "Users can update their own profile"
  ON public.profiles FOR UPDATE
  USING (auth.uid() = id);

CREATE POLICY "RRHH can view all profiles"
  ON public.profiles FOR SELECT
  USING (public.has_role(auth.uid(), 'analista_rrhh'));

-- Tabla de colaboradores (maestro completo)
CREATE TABLE public.colaboradores (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  dni VARCHAR(8) NOT NULL UNIQUE,
  apellidos TEXT NOT NULL,
  nombres TEXT NOT NULL,
  fecha_nacimiento DATE NOT NULL,
  categoria categoria_colaborador NOT NULL,
  sexo sexo_colaborador NOT NULL,
  celular VARCHAR(15),
  area_operacion TEXT NOT NULL,
  tipo_contrato TEXT NOT NULL,
  sede TEXT NOT NULL,
  activo BOOLEAN DEFAULT true NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

ALTER TABLE public.colaboradores ENABLE ROW LEVEL SECURITY;

-- Políticas RLS para colaboradores
CREATE POLICY "Colaboradores can view their own record"
  ON public.colaboradores FOR SELECT
  USING (user_id = auth.uid());

CREATE POLICY "RRHH can view all colaboradores"
  ON public.colaboradores FOR SELECT
  USING (public.has_role(auth.uid(), 'analista_rrhh'));

CREATE POLICY "RRHH can insert colaboradores"
  ON public.colaboradores FOR INSERT
  WITH CHECK (public.has_role(auth.uid(), 'analista_rrhh'));

CREATE POLICY "RRHH can update colaboradores"
  ON public.colaboradores FOR UPDATE
  USING (public.has_role(auth.uid(), 'analista_rrhh'));

-- Tabla de descansos médicos
CREATE TABLE public.descansos_medicos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  colaborador_id UUID REFERENCES public.colaboradores(id) ON DELETE CASCADE NOT NULL,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  fecha_inicio DATE NOT NULL,
  fecha_fin DATE NOT NULL,
  imagen_url TEXT,
  estado estado_descanso DEFAULT 'Pendiente' NOT NULL,
  comentario_rrhh TEXT,
  sede TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

ALTER TABLE public.descansos_medicos ENABLE ROW LEVEL SECURITY;

-- Políticas RLS para descansos médicos
CREATE POLICY "Users can view their own descansos"
  ON public.descansos_medicos FOR SELECT
  USING (user_id = auth.uid());

CREATE POLICY "Users can create their own descansos"
  ON public.descansos_medicos FOR INSERT
  WITH CHECK (user_id = auth.uid());

CREATE POLICY "RRHH can view all descansos"
  ON public.descansos_medicos FOR SELECT
  USING (public.has_role(auth.uid(), 'analista_rrhh'));

CREATE POLICY "RRHH can update descansos"
  ON public.descansos_medicos FOR UPDATE
  USING (public.has_role(auth.uid(), 'analista_rrhh'));

-- Función para actualizar updated_at
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers para actualizar updated_at
CREATE TRIGGER update_profiles_updated_at
  BEFORE UPDATE ON public.profiles
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_colaboradores_updated_at
  BEFORE UPDATE ON public.colaboradores
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_descansos_updated_at
  BEFORE UPDATE ON public.descansos_medicos
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();

-- Función para crear perfil al registrarse
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.profiles (id, dni, apellidos, nombres)
  VALUES (
    NEW.id,
    NEW.raw_user_meta_data->>'dni',
    NEW.raw_user_meta_data->>'apellidos',
    NEW.raw_user_meta_data->>'nombres'
  );
  RETURN NEW;
END;
$$;

-- Trigger para crear perfil automáticamente
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user();

-- Crear bucket de storage para certificados médicos
INSERT INTO storage.buckets (id, name, public)
VALUES ('certificados-medicos', 'certificados-medicos', false)
ON CONFLICT (id) DO NOTHING;

-- Políticas de storage para certificados médicos
CREATE POLICY "Users can upload their own certificados"
  ON storage.objects FOR INSERT
  WITH CHECK (
    bucket_id = 'certificados-medicos' AND
    auth.uid()::text = (storage.foldername(name))[1]
  );

CREATE POLICY "Users can view their own certificados"
  ON storage.objects FOR SELECT
  USING (
    bucket_id = 'certificados-medicos' AND
    auth.uid()::text = (storage.foldername(name))[1]
  );

CREATE POLICY "RRHH can view all certificados"
  ON storage.objects FOR SELECT
  USING (
    bucket_id = 'certificados-medicos' AND
    public.has_role(auth.uid(), 'analista_rrhh')
  );