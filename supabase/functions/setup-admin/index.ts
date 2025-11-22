import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.84.0'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!
    const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    const supabase = createClient(supabaseUrl, supabaseServiceKey)

    const dni = '11111111'
    const email = `${dni}@sistema.local`
    const password = '11111111'

    // Check if user already exists
    const { data: existingProfile } = await supabase
      .from('profiles')
      .select('id')
      .eq('dni', dni)
      .maybeSingle()

    if (existingProfile) {
      return new Response(
        JSON.stringify({ 
          message: 'Usuario administrador ya existe',
          user_id: existingProfile.id 
        }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
      )
    }

    // Create the admin user
    const { data: authData, error: authError } = await supabase.auth.admin.createUser({
      email,
      password,
      email_confirm: true,
      user_metadata: {
        dni,
        apellidos: 'Administrador',
        nombres: 'RRHH'
      }
    })

    if (authError) throw authError

    console.log('Usuario administrador creado:', authData.user.id)

    // Assign analista_rrhh role
    const { error: roleError } = await supabase
      .from('user_roles')
      .insert({
        user_id: authData.user.id,
        role: 'analista_rrhh'
      })

    if (roleError) throw roleError

    console.log('Rol analista_rrhh asignado al usuario administrador')

    return new Response(
      JSON.stringify({ 
        message: 'Usuario administrador creado exitosamente',
        user_id: authData.user.id,
        email,
        dni
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
    )

  } catch (error) {
    console.error('Error creando usuario administrador:', error)
    const errorMessage = error instanceof Error ? error.message : 'Error desconocido'
    return new Response(
      JSON.stringify({ error: errorMessage }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 500 }
    )
  }
})
