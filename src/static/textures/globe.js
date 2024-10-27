import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { getFresnelMat } from '/static/assets/getFresnelMat.js';

//Making the globe------------------------------------------------
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ canvas: document.getElementById('sphereCanvas'), alpha: true });
renderer.setClearColor(0x000000, 0);
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setSize(window.innerWidth * 0.5, window.innerHeight * 0.5);

const geometry = new THREE.SphereGeometry(3, 32, 32);
const loader = new THREE.TextureLoader();
const texture = loader.load("/static/textures/earthDay.jpg");
const material = new THREE.MeshStandardMaterial({ map: texture });

const earthGroup = new THREE.Group();
scene.add(earthGroup);

const sphere = new THREE.Mesh(geometry, material);
earthGroup.add(sphere);

const sunLight = new THREE.DirectionalLight(0xffffff);
sunLight.position.set(-2, 0.5, 0.2);
scene.add(sunLight);

const ambientLight = new THREE.AmbientLight(0x404040);
scene.add(ambientLight);

const lightsMat = new THREE.MeshBasicMaterial({
    map: loader.load("/static/textures/earthNight.jpg"),
    blending: THREE.AdditiveBlending
});

const cloudsMat = new THREE.MeshBasicMaterial({
    map: loader.load("/static/textures/earthClouds.jpg"),
    blending: THREE.AdditiveBlending,
    transparent: true,
    opacity: 0.4,  
    depthWrite: false,
    depthTest: true
});

const cloudsGeometry = new THREE.SphereGeometry(3.01, 32, 32);
const cloudsMesh = new THREE.Mesh(cloudsGeometry, cloudsMat);
earthGroup.add(cloudsMesh);

const lightsMesh = new THREE.Mesh(geometry, lightsMat);
earthGroup.add(lightsMesh);

camera.position.z = 5;
scene.fog = new THREE.Fog(0x4f46e5, 5, 15);

const fresnelMat = getFresnelMat();
const glowMesh = new THREE.Mesh(geometry, fresnelMat);
glowMesh.scale.setScalar(1.01);
earthGroup.add(glowMesh);
//----------------------------------------------------------------------------

//planes with a plane asset--------------------------
class Plane {
    constructor(color) {
        this.mesh = null;
        this.color = color;
    }

    async initialize() {
        return new Promise((resolve, reject) => {
            const glftLoader = new GLTFLoader();
            glftLoader.load(
                '/static/assets/plane/scene.gltf',
                (gltf) => {
                    this.mesh = gltf.scene;
                    
                    this.mesh.scale.set(0.1, 0.1, 0.1);//size of plane
                    
                    // color the planes
                    this.mesh.traverse((child) => {
                        if (child.isMesh) {
                            child.material = new THREE.MeshStandardMaterial({
                                color: this.color,
                                metalness: 0.7,
                                roughness: 0.3
                            });
                        }
                    });
                    
                    resolve(this.mesh);
                },
                undefined,
                (error) => {
                    console.error('An error occurred loading the GLTF model:', error);
                    reject(error);
                }
            );
        });
    }

    getMesh() {
        return this.mesh;
    }
}

async function createPlane(index) {
    const colors = [0xf44b42, 0x41f4a0, 0x4164f4];
    const plane = new Plane(colors[index % colors.length]);
    
    try {
        const planeMesh = await plane.initialize();
        
        const radius = 3;
        const theta = Math.random() * Math.PI * 2;
        const phi = Math.random() * Math.PI;

        planeMesh.position.x = radius * Math.sin(phi) * Math.cos(theta);
        planeMesh.position.y = radius * Math.sin(phi) * Math.sin(theta);
        planeMesh.position.z = radius * Math.cos(phi);

        planeMesh.userData = {
            orbitRadius: radius,
            orbitSpeed: 0.001 + (Math.random() * 0.002),
            verticalOffset: Math.random() * Math.PI * 2,
            phase: Math.random() * Math.PI * 2
        };

        planesGroup.add(planeMesh);
        return planeMesh;
    } catch (error) {
        console.error('Failed to create plane:', error);
        return null;
    }
}

async function initializePlanes() {
    const planePromises = Array(50).fill(null).map((_, i) => createPlane(i));
    return Promise.all(planePromises);
}

const planes = [];
initializePlanes().then(createdPlanes => {
    planes.push(...createdPlanes.filter(plane => plane !== null));
});

const planesGroup = new THREE.Group();
earthGroup.add(planesGroup);
//-----------------------------------------------------------------------

//These are event listeners to interact with the sphere
let shouldRotate = true;
const canvas = document.getElementById('sphereCanvas');

canvas.addEventListener('mouseenter', () => {
    shouldRotate = false;
    earthGroup.scale.set(1.02, 1.02, 1.02);
});

canvas.addEventListener('mouseleave', () => {
    isDragging = false;
    shouldRotate = true;
    earthGroup.scale.set(1, 1, 1);
});

window.addEventListener('resize', () => {
    renderer.setSize(window.innerWidth * 0.5, window.innerHeight * 0.5);
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
});

let isDragging = false;
let previousMousePosition = { x: 0, y: 0 };

canvas.addEventListener('mousedown', (event) => {
    isDragging = true;
    previousMousePosition = { x: event.clientX, y: event.clientY };
});

canvas.addEventListener('mouseup', () => {
    isDragging = false;
});

canvas.addEventListener('mousemove', (event) => {
    if (isDragging) {
        const deltaMove = {
            x: event.clientX - previousMousePosition.x,
            y: event.clientY - previousMousePosition.y
        };
        earthGroup.rotation.y += deltaMove.x * 0.002;
        earthGroup.rotation.x += deltaMove.y * 0.002;

        previousMousePosition = { x: event.clientX, y: event.clientY };
    }
});

function animate() {
    requestAnimationFrame(animate);

    if (shouldRotate) {
        earthGroup.rotation.y += 0.001;
    }

    // plane orbits
    planes.forEach(plane => {
        const params = plane.userData;
        params.phase += params.orbitSpeed; // move the planes along the orbit

        // orbit effect
        const radius = params.orbitRadius;
        const altitude = Math.sin(params.phase + params.verticalOffset) * 2; 

        plane.position.x = radius * Math.cos(params.phase); // Circular path on X-axis
        plane.position.z = radius * Math.sin(params.phase); // Circular path on Z-axis
        plane.position.y = altitude;

        // Make the planes look forward
        plane.lookAt(earthGroup.position); // make planes face the globe
        plane.rotateY(Math.PI / 2);
    });

    renderer.render(scene, camera);
}

animate();
