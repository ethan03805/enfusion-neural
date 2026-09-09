#ifdef WORKBENCH
class ENR_MaterialRoom
{
 static bool Attempted;
 static ref Resource ModelResource;
 static IEntity RoomEntity;

 static void Init(BaseWorld world)
 {
  if (Attempted) return;
  Attempted = true;
  ModelResource = Resource.Load(ENR_RoomConfig.Model);
  if (!ModelResource || !ModelResource.IsValid())
  {
   Print("ENR_ROOM failed=model_load");
   return;
  }
  MeshObject mesh = ModelResource.GetResource().ToMeshObject();
  if (!mesh) { Print("ENR_ROOM failed=mesh_type"); return; }
  EntitySpawnParams parameters = new EntitySpawnParams();
  parameters.TransformMode = ETransformMode.WORLD;
  Math3D.MatrixIdentity4(parameters.Transform);
  parameters.Transform[3] = ENR_RoomConfig.Origin;
  RoomEntity = GetGame().SpawnEntity(GenericEntity, world, parameters);
  if (!RoomEntity) { Print("ENR_ROOM failed=spawn"); return; }
  RoomEntity.SetName("ENR_original_material_room");
  RoomEntity.SetObject(mesh, "");
  RoomEntity.SetFlags(EntityFlags.VISIBLE);
  RoomEntity.Update();
  vector mins, maxs;
  RoomEntity.GetBounds(mins, maxs);
  string materials[64];
  int count = mesh.GetMaterials(materials);
  PrintFormat("ENR_ROOM spawned origin=%1 mins=%2 maxs=%3 materials=%4", RoomEntity.GetOrigin(), mins, maxs, count);
 }
}
#endif
