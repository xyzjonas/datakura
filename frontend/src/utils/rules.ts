type Anything = string | number | undefined | null

export const rules = {
  notEmpty: (val: Anything) => !!val || 'Pole nesmí být prazdné',
  isNumber: (val: number) => !isNaN(val) || 'Pole musí být číslo',
  atLeastZero: (val: number) => val >= 0 || 'Pole musí být číslo větší nebo rovno 0',
  atLeastOne: (val: number) => val > 0 || 'Pole musí být číslo větší než 0',
  max9999: (val: number) => val < 9999 || 'Pole nesmí být číslo větší než 9999',
  max99999: (val: number) => val < 999999 || 'Pole nesmí být číslo větší než 999999',
  isPercentage: (val: number) => (val >= 0 && val <= 100) || 'Pole musí být procento mezi 0 a 100',
}
