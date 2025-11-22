-- Drop existing trigger if exists
DROP TRIGGER IF EXISTS on_auth_user_created_assign_role ON auth.users;

-- Recreate the trigger on auth.users to assign default role
CREATE TRIGGER on_auth_user_created_assign_role
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user_role();

-- Fix existing users without roles by assigning them the colaborador role
INSERT INTO public.user_roles (user_id, role)
SELECT id, 'colaborador'::app_role
FROM auth.users
WHERE id NOT IN (SELECT user_id FROM public.user_roles)
ON CONFLICT (user_id, role) DO NOTHING;