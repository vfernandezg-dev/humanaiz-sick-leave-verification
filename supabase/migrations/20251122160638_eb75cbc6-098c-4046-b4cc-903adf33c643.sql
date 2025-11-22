-- Agregar políticas faltantes para user_roles
CREATE POLICY "Users can view their own roles"
  ON public.user_roles FOR SELECT
  USING (user_id = auth.uid());

CREATE POLICY "RRHH can view all roles"
  ON public.user_roles FOR SELECT
  USING (public.has_role(auth.uid(), 'analista_rrhh'));

CREATE POLICY "RRHH can insert roles"
  ON public.user_roles FOR INSERT
  WITH CHECK (public.has_role(auth.uid(), 'analista_rrhh'));

-- Corregir search_path para handle_new_user
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

-- Corregir search_path para update_updated_at_column
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = public
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;