-- Create function to handle user role assignment
CREATE OR REPLACE FUNCTION public.handle_new_user_role()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  -- Insert default colaborador role for new users
  INSERT INTO public.user_roles (user_id, role)
  VALUES (NEW.id, 'colaborador');
  RETURN NEW;
END;
$$;

-- Create trigger to automatically assign colaborador role on signup
DROP TRIGGER IF EXISTS on_auth_user_created_assign_role ON auth.users;
CREATE TRIGGER on_auth_user_created_assign_role
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user_role();