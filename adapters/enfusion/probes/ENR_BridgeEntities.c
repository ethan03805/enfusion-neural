#ifdef WORKBENCH
// Optional set dressing inside the private simulation. Prefab names were observed
// through Workbench.SearchResources. Runtime placement still needs visual review.
class ENR_BridgeEntities
{
 static bool Attempted;
 static ref array<IEntity> Spawned = {};

 static void Spawn(BaseWorld world, ResourceName name, vector position, vector direction)
 {
  // Query the simulation world. The editor API returned zero while the game
  // simulation was active and placed the first Everon test below the terrain.
  position[1] = world.GetSurfaceY(position[0], position[2]) + 0.15;
  PrintFormat("ENR_PROP ground resource=%1 position=%2", name, position);
  Resource resource = Resource.Load(name);
  if (!resource || !resource.IsValid()) { PrintFormat("ENR_PROP failed resource=%1", name); return; }
  EntitySpawnParams parameters = new EntitySpawnParams();
  parameters.TransformMode = ETransformMode.WORLD;
  Math3D.MatrixIdentity4(parameters.Transform);
  Math3D.DirectionAndUpMatrix(direction, "0 1 0", parameters.Transform);
  parameters.Transform[3] = position;
  IEntity entity = GetGame().SpawnEntityPrefab(resource, world, parameters);
  if (!entity) { PrintFormat("ENR_PROP failed spawn=%1", name); return; }
  Spawned.Insert(entity);
  PrintFormat("ENR_PROP spawned resource=%1 position=%2", name, entity.GetOrigin());
 }

 static void Init(BaseWorld world)
 {
  if (Attempted || !ENR_BridgeConfig.Entities) return;
  Attempted = true;
  vector forward = ENR_Sequence.Direction();
  vector right = Vector(forward[2], 0, -forward[0]);
  Spawn(world, "{5674FAEB9AB7BDD0}Prefabs/Vehicles/Wheeled/M998/M998_uncovered.et", ENR_SequenceConfig.Start + 9 * forward - 2.5 * right, forward);
  Spawn(world, "{26A9756790131354}Prefabs/Characters/Factions/BLUFOR/US_Army/Character_US_Rifleman.et", ENR_SequenceConfig.Start + 6 * forward + 2 * right, -forward);
 }

 static void Record()
 {
  foreach (IEntity entity : Spawned)
  {
   if (entity) PrintFormat("ENR_PROP at_capture name=%1 position=%2 yaw_pitch_roll=%3", entity.GetName(), entity.GetOrigin(), entity.GetYawPitchRoll());
  }
 }
}
#endif
