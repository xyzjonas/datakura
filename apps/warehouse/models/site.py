#
# class Site(BaseModel):
#     """Site or 'context' of a subsection of all the """
#
#     name = models.CharField(max_length=255, null=False, unique=True)
#     parent = models.ForeignKey(
#         "ProductGroup",
#         null=True,
#         blank=True,
#         on_delete=models.CASCADE,
#         related_name="children",
#     )
#
#     def __str__(self) -> str:
#         return self.name
