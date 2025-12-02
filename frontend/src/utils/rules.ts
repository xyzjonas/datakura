type Anything = string | number | undefined | null

export const rules = {
  notEmpty: (val: Anything) => !!val || 'Pole nesmí být prazdné',
  isNumber: (val: number) => !isNaN(val) || 'Pole musí být číslo',
  atLeastOne: (val: number) => val > 0 || 'Pole musí být číslo větší než 0',
  max9999: (val: number) => val < 9999 || 'Pole nesmí být číslo větší než 9999',
}
