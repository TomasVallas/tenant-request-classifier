interface ExampleButtonsProps {
  onSelect: (text: string) => void
  disabled: boolean
}

const EXAMPLES = [
  { label: 'Vika', text: 'Keittiön hana vuotaa, asunto B12.' },
  { label: 'Laskutus', text: 'Sain tämän kuun vuokralaskun kahteen kertaan, asunto C4.' },
  { label: 'Muutto', text: 'Haluan irtisanoa vuokrasopimukseni maaliskuun lopussa, asunto D9.' },
  {
    label: 'Kiireellinen',
    text: 'Kylpyhuoneessa on vesivuoto ja vettä valuu käytävään, asunto A3.',
  },
]

export function ExampleButtons({ onSelect, disabled }: ExampleButtonsProps) {
  return (
    <fieldset className="examples">
      <legend className="examples__legend">Kokeile esimerkkiä</legend>
      <div className="examples__buttons">
        {EXAMPLES.map((example) => (
          <button
            key={example.label}
            type="button"
            className="button button--chip"
            disabled={disabled}
            onClick={() => onSelect(example.text)}
          >
            {example.label}
          </button>
        ))}
      </div>
    </fieldset>
  )
}
