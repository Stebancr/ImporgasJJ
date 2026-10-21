module.exports=async function chooseLocation(page,label,value){
 const names={'76001000':'Cali','11001000':'Bogota'}
 const input=page.getByRole('combobox',{name:label,exact:true})
 await input.click()
 await input.fill(names[value]||value)
 await page.getByRole('listbox').getByRole('option').first().click()
}