-- Function to create colaborador record when user signs up
CREATE OR REPLACE FUNCTION public.handle_new_user_colaborador()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  -- Insert colaborador record with default values
  INSERT INTO public.colaboradores (
    user_id,
    dni,
    apellidos,
    nombres,
    area_operacion,
    tipo_contrato,
    sede,
    sexo,
    categoria,
    fecha_nacimiento
  ) VALUES (
    NEW.id,
    NEW.raw_user_meta_data->>'dni',
    NEW.raw_user_meta_data->>'apellidos',
    NEW.raw_user_meta_data->>'nombres',
    'Por definir',
    'Por definir',
    'Por definir',
    'M',
    'D',
    CURRENT_DATE
  );
  
  RETURN NEW;
END;
$$;

-- Create trigger on auth.users to auto-create colaborador
DROP TRIGGER IF EXISTS on_auth_user_created_colaborador ON auth.users;
CREATE TRIGGER on_auth_user_created_colaborador
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user_colaborador();

-- Create colaborador records for existing users without one
INSERT INTO public.colaboradores (
  user_id,
  dni,
  apellidos,
  nombres,
  area_operacion,
  tipo_contrato,
  sede,
  sexo,
  categoria,
  fecha_nacimiento
)
SELECT 
  u.id,
  u.raw_user_meta_data->>'dni',
  u.raw_user_meta_data->>'apellidos',
  u.raw_user_meta_data->>'nombres',
  'Por definir',
  'Por definir',
  'Por definir',
  'M',
  'D',
  CURRENT_DATE
FROM auth.users u
LEFT JOIN public.colaboradores c ON c.user_id = u.id
WHERE c.id IS NULL
  AND u.raw_user_meta_data->>'dni' IS NOT NULL
ON CONFLICT (dni) DO NOTHING;