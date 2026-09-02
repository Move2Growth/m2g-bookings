'use client'

import { useEffect, useState } from 'react'
import { FichaSalon, type SalonEnLista } from '@/componentes/ficha-salon'
import { conSesion, leerSesion } from '@/lib/sesion'

/**
 * La lista de resultados.
 *
 * Recibe los salones **ya resueltos en el servidor**, así que el HTML que ve Google lleva los
 * nombres, los precios y las notas. Lo único que se resuelve en el navegador es cuáles están
 * guardados, que depende de quién mira y por tanto no se puede cachear ni indexar.
 *
 * Los corazones aparecen medio segundo después de la lista. Es a propósito: preferimos que la
 * lista se vea entera cuanto antes a que se retrase por un dato que solo decora.
 */
export function ListaSalones({ salones }: { salones: SalonEnLista[] }) {
  const [guardados, setGuardados] = useState<Set<string> | null>(null)

  useEffect(() => {
    const sesion = leerSesion()
    if (!sesion) {
      setGuardados(new Set())
      return
    }
    conSesion<{ slug: string }[]>('/api/v1/mi/favoritos', { token: sesion.acceso })
      .then((lista) => setGuardados(new Set(lista.map((f) => f.slug))))
      // Que fallen los guardados no puede tumbar la lista: se queda sin corazones marcados.
      .catch(() => setGuardados(new Set()))
  }, [])

  return (
    <ul className="salones escalona">
      {salones.map((s) => (
        <FichaSalon
          key={s.slug}
          salon={s}
          guardado={guardados?.has(s.slug)}
          onGuardar={(slug, ahora) =>
            setGuardados((previos) => {
              const siguiente = new Set(previos ?? [])
              if (ahora) siguiente.add(slug)
              else siguiente.delete(slug)
              return siguiente
            })
          }
        />
      ))}
    </ul>
  )
}
