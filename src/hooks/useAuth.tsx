import { useEffect, useState } from "react";
import { User, Session } from "@supabase/supabase-js";
import { supabase } from "@/integrations/supabase/client";
import { useToast } from "@/hooks/use-toast";

export type UserRole = "colaborador" | "analista_rrhh";

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [role, setRole] = useState<UserRole | null>(null);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  useEffect(() => {
    // Set up auth listener
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, session) => {
        setSession(session);
        setUser(session?.user ?? null);
        
        if (session?.user) {
          // Fetch user role
          setTimeout(() => {
            fetchUserRole(session.user.id);
          }, 0);
        } else {
          setRole(null);
          setLoading(false);
        }
      }
    );

    // Check for existing session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setUser(session?.user ?? null);
      
      if (session?.user) {
        fetchUserRole(session.user.id);
      } else {
        setLoading(false);
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  const fetchUserRole = async (userId: string) => {
    try {
      const { data, error } = await supabase
        .from("user_roles")
        .select("role")
        .eq("user_id", userId)
        .single();

      if (error) throw error;
      setRole(data.role as UserRole);
    } catch (error) {
      console.error("Error fetching role:", error);
      setRole(null);
    } finally {
      setLoading(false);
    }
  };

  const signIn = async (dni: string, password: string) => {
    try {
      const { data: profile } = await supabase
        .from("profiles")
        .select("id")
        .eq("dni", dni)
        .single();

      if (!profile) {
        throw new Error("DNI no encontrado");
      }

      // Get email from auth.users
      const { data: userData } = await supabase
        .from("profiles")
        .select("*")
        .eq("id", profile.id)
        .single();

      // Use DNI as email format for authentication
      const email = `${dni}@sistema.local`;
      
      const { error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) throw error;

      toast({
        title: "Inicio de sesión exitoso",
        description: "Bienvenido al sistema",
      });

      return { error: null };
    } catch (error: any) {
      toast({
        title: "Error al iniciar sesión",
        description: error.message,
        variant: "destructive",
      });
      return { error };
    }
  };

  const signUp = async (
    dni: string,
    password: string,
    apellidos: string,
    nombres: string
  ) => {
    try {
      if (dni.length !== 8) {
        throw new Error("El DNI debe tener 8 dígitos");
      }

      const email = `${dni}@sistema.local`;
      const redirectUrl = `${window.location.origin}/`;

      const { error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          emailRedirectTo: redirectUrl,
          data: {
            dni,
            apellidos,
            nombres,
          },
        },
      });

      if (error) throw error;

      // Assign colaborador role by default
      const { data: { user } } = await supabase.auth.getUser();
      if (user) {
        await supabase.from("user_roles").insert({
          user_id: user.id,
          role: "colaborador",
        });
      }

      toast({
        title: "Registro exitoso",
        description: "Tu cuenta ha sido creada correctamente",
      });

      return { error: null };
    } catch (error: any) {
      toast({
        title: "Error al registrarse",
        description: error.message,
        variant: "destructive",
      });
      return { error };
    }
  };

  const signOut = async () => {
    try {
      const { error } = await supabase.auth.signOut();
      if (error) throw error;

      toast({
        title: "Sesión cerrada",
        description: "Has cerrado sesión correctamente",
      });
    } catch (error: any) {
      toast({
        title: "Error al cerrar sesión",
        description: error.message,
        variant: "destructive",
      });
    }
  };

  return {
    user,
    session,
    role,
    loading,
    signIn,
    signUp,
    signOut,
  };
}
